from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db import models
from django.utils.timezone import now
from rest_framework.pagination import LimitOffsetPagination
from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from rest_framework.generics import ListAPIView
from geopy.distance import geodesic


from .models import (
    Hueco, Confirmacion, Comentario,
    PuntosUsuario, HistorialHueco, ValidacionHueco, Suscripcion,
    EstadoHueco, DenunciaHueco
)
from .serializers import (
    HuecoSerializer, ConfirmacionSerializer,
    ComentarioSerializer, PuntosUsuarioSerializer,
    ValidacionHuecoSerializer, DenunciaHuecoSerializer
)

from apps.huecos.services.hueco_service import get_huecos_cercanos
from apps.huecos.services.puntos_service import registrar_puntos
from apps.huecos.services.validacion_service import procesar_validacion


class HuecoViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal de huecos:
    - Crea nuevos reportes
    - Reabre huecos cerrados si están cerca
    - Asigna puntos y registra historial automáticamente
    - Limita a 20 reportes diarios por usuario
    """
    queryset = Hueco.objects.filter(status=1, is_deleted=False).order_by('-fecha_reporte')
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Incrementar vistas (Redis optimizado)
        try:
            cache_key = f"hueco_vistas_{instance.id}"
            try:
                cache.incr(cache_key)
            except ValueError:
                cache.set(cache_key, 1, timeout=None)
            instance.vistas += 1 
        except Exception:
            # Fallback
            instance.vistas += 1
            instance.save(update_fields=['vistas'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # Sobrescribimos create para manejar la lógica de reapertura de forma limpia
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ejecutar lógica y capturar el hueco (nuevo o reabierto)
        hueco = self.perform_create(serializer)
        
        # Si perform_create devolvió un hueco que ya existía (reapertura o duplicado)
        if hasattr(hueco, '_reabierto') or hasattr(hueco, '_ya_reportado'):
            return Response(self.get_serializer(hueco).data, status=status.HTTP_200_OK)
            
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        from django.db import transaction
        user = self.request.user
        hoy = now().date()

        with transaction.atomic():
            # 1️⃣ Límite diario
            reportes_hoy = Hueco.objects.filter(usuario=user, fecha_reporte__date=hoy).count()
            if reportes_hoy >= 20:
                raise serializers.ValidationError("Límite diario de 20 reportes alcanzado.")

            # 2️⃣ Revisión de huecos cercanos
            lat = self.request.data.get('latitud')
            lon = self.request.data.get('longitud')
            hueco_existente = None

            if lat and lon:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    cercanos = get_huecos_cercanos(lat_f, lon_f, radio_metros=20)
                    for h, _ in cercanos:
                        # Casos 1 & 2: Si ya está reportado y sigue vigente, no crear otro!
                        if h.estado in [EstadoHueco.PENDIENTE, EstadoHueco.ACTIVO, EstadoHueco.REABIERTO, EstadoHueco.EN_REPARACION]:
                            h._ya_reportado = True
                            return h
                            
                        # Caso 3: Si ya estaba arreglado o cerrado, entonces sí lo reabrimos
                        if h.estado in [EstadoHueco.CERRADO, EstadoHueco.REPARADO]:
                            hueco_existente = h
                            break
                except (ValueError, TypeError, Exception):
                    # Evitamos que cualquier fallo en geolocalización rompa el guardado
                    pass

            # 2.2️⃣ Validación: Usuario cerca del Hueco (Anti-fraude)
            # Esperamos 'user_lat' y 'user_lon' desde la App
            user_lat = self.request.data.get('user_lat')
            user_lon = self.request.data.get('user_lon')
            if user_lat and user_lon and lat and lon:
                try:
                    u_lat = float(user_lat)
                    u_lon = float(user_lon)
                    dist_usuario = geodesic((u_lat, u_lon), (lat_f, lon_f)).meters
                    if dist_usuario > 100: # Límite de 100 metros
                        raise serializers.ValidationError(
                            f"Estás muy lejos del hueco ({int(dist_usuario)}m). "
                            "Debes estar a menos de 100m para reportarlo."
                        )
                except (ValueError, TypeError):
                    pass

            # 3️⃣ Reapertura si corresponde (porque estaba reparado/cerrado)
            if hueco_existente:
                hueco_existente.estado = EstadoHueco.REABIERTO
                hueco_existente.numero_ciclos += 1
                hueco_existente.fecha_actualizacion = now()
                hueco_existente.save(update_fields=['estado', 'numero_ciclos', 'fecha_actualizacion'])

                HistorialHueco.objects.create(
                    hueco=hueco_existente,
                    usuario=user,
                    accion=f"Hueco reabierto por {user.username} (desde ubicación)"
                )

                registrar_puntos(user, 5, "reapertura", f"Reapertura del hueco #{hueco_existente.id}")
                from apps.huecos.services.notificacion_service import notificar_reapertura
                
                notificar_reapertura(hueco_existente, user)
                hueco_existente._reabierto = True
                return hueco_existente

            # 4️⃣ Crear nuevo hueco
            # 0️⃣ Imagen obligatoria para nuevos reportes
            if not self.request.FILES.get('imagen'):
                raise serializers.ValidationError({"imagen": "La foto del hueco es obligatoria para crear un reporte."})

            # Guardamos de una vez con status=1 (BaseStatusModel)
            hueco = serializer.save(usuario=user, created_by=user, status=1)
            registrar_puntos(user, 10, "reporte", f"Nuevo reporte de hueco #{hueco.id}")

            HistorialHueco.objects.create(
                hueco=hueco,
                usuario=user,
                accion="Reporte de hueco creado"
            )

            return hueco

    @action(detail=True, methods=['post'], url_path='follow')
    def follow(self, request, pk=None):
        hueco = self.get_object()
        user = request.user

        sus, created = Suscripcion.objects.get_or_create(
            usuario=user,
            hueco=hueco,
            defaults={'status': 1}
        )

        if not created and sus.status == 1:
            return Response({"detail": "Ya sigues este hueco."}, status=status.HTTP_200_OK)

        sus.status = 1
        sus.save(update_fields=['status'])

        return Response({"detail": "Hueco seguido correctamente."})

    @action(detail=True, methods=['post'], url_path='unfollow')
    def unfollow(self, request, pk=None):
        hueco = self.get_object()
        user = request.user

        try:
            sus = Suscripcion.objects.get(usuario=user, hueco=hueco)
            sus.status = 0
            sus.save(update_fields=['status'])
            return Response({"detail": "Has dejado de seguir este hueco."})
        except Suscripcion.DoesNotExist:
            return Response({"detail": "No sigues este hueco."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reportar')
    def reportar(self, request, pk=None):
        """Permite a los usuarios denunciar contenido inapropiado o falso"""
        hueco = self.get_object()
        user = request.user
        motivo = request.data.get('motivo', 'other')
        comentario = request.data.get('comentario', '')

        if DenunciaHueco.objects.filter(hueco=hueco, usuario=user).exists():
            return Response({"detail": "Ya has reportado este contenido."}, status=status.HTTP_400_BAD_REQUEST)

        DenunciaHueco.objects.create(
            hueco=hueco,
            usuario=user,
            motivo=motivo,
            comentario=comentario
        )
        
        hueco.refresh_from_db()
        if hueco.is_deleted:
             return Response({"detail": "Gracias por reportar. El contenido ha sido removido."}, status=status.HTTP_200_OK)

        return Response({"detail": "Denuncia recibida correctamente."}, status=status.HTTP_201_CREATED)


class ConfirmacionViewSet(viewsets.ModelViewSet):
    queryset = Confirmacion.objects.all().order_by('-fecha')
    serializer_class = ConfirmacionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # 1. Validar datos
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        hueco = serializer.validated_data['hueco']
        nuevo_estado = serializer.validated_data['nuevo_estado'] # Integer
        user = request.user
        
        # 2. Upsert con Ciclos
        defaults = {
            'nuevo_estado': nuevo_estado,
            'fecha': now()
        }

        # El voto se asocia al ciclo actual del hueco
        ciclo_actual = hueco.numero_ciclos

        obj, created = Confirmacion.objects.update_or_create(
            hueco=hueco,
            usuario=user,
            numero_ciclo=ciclo_actual,
            defaults=defaults
        )

        # 3. Asignar puntos solo si es nuevo registro
        if created:
            registrar_puntos(user, 2, "confirmacion", f"Confirmación del hueco #{hueco.id}")
            HistorialHueco.objects.create(
                hueco=hueco,
                usuario=user,
                accion=f"Voto por estado: {nuevo_estado}"
            )
            return Response(ConfirmacionSerializer(obj).data, status=status.HTTP_201_CREATED)
        
        return Response(ConfirmacionSerializer(obj).data, status=status.HTTP_200_OK)


class ComentarioViewSet(viewsets.ModelViewSet):
    queryset = Comentario.objects.all().order_by('-fecha')
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['hueco']

    def perform_create(self, serializer):
        comentario = serializer.save(usuario=self.request.user)
        registrar_puntos(self.request.user, 1, "comentario", f"Comentario en hueco #{comentario.hueco.id}")


class PuntosUsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """Permite listar los puntos y ver el ranking general"""
    queryset = PuntosUsuario.objects.all().order_by('-fecha')
    serializer_class = PuntosUsuarioSerializer

    def list(self, request, *args, **kwargs):
        ranking = (
            PuntosUsuario.objects.values('usuario__username')
            .annotate(total=models.Sum('puntos'))
            .order_by('-total')
        )
        return Response(ranking)


class ValidacionHuecoViewSet(viewsets.ModelViewSet):
    """
    Los usuarios validan si un hueco realmente existe o no.
    - Se pondera el voto según reputación
    - Se evalúan los resultados acumulados
    - Se asignan puntos y reputación
    """
    queryset = ValidacionHueco.objects.all()
    serializer_class = ValidacionHuecoSerializer

    def perform_create(self, serializer):
        usuario = self.request.user
        # Guardar validación: Esto disparará el signal actualizar_estado_hueco en signals.py
        # el cual a su vez llamará al servicio procesar_validacion de forma limpia.
        return serializer.save(usuario=usuario)


class HuecosCercanosViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista huecos cercanos por ubicación o ciudad.
    Mantiene queryset válido para DRF y agrega distancia ordenada.
    """
    queryset = Hueco.objects.all()
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        request = self.request
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        ciudad = request.query_params.get('ciudad')
        radio_param = request.query_params.get('radio', 1000)

        # --- Validación de radio ---
        try:
            radio = float(radio_param)
        except ValueError:
            radio = 1000

        # --- Clave de cache ---
        cache_key = f"hc_{lat}_{lon}_{radio}_{ciudad}"
        cached_qs = cache.get(cache_key)
        if cached_qs is not None:
            return cached_qs

        # --- Query base (ESTADOS que quieres incluir) ---
        # --- Query base (ESTADOS que quieres incluir) ---
        qs = Hueco.objects.filter(
            estado__in=[
                EstadoHueco.PENDIENTE, 
                EstadoHueco.CERRADO, 
                EstadoHueco.REABIERTO, 
                EstadoHueco.ACTIVO,
                EstadoHueco.EN_REPARACION,
                EstadoHueco.REPARADO
            ],
            status=1,
            is_deleted=False
        )

        # --- Filtrar por ciudad (si aplica) ---
        if ciudad:
            qs = qs.filter(descripcion__icontains=ciudad)

        # --- Si hay lat/lon, calcular distancias ---
        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)

                # Obtener lista de huecos cercanos desde el servicio
                cercanos = get_huecos_cercanos(lat, lon, radio_metros=radio)

                # Extraer IDS en orden por distancia
                ids_en_orden = [h.id for h, _ in cercanos]

                if not ids_en_orden:
                    cache.set(cache_key, Hueco.objects.none(), 300)
                    return Hueco.objects.none()

                # Convertir la lista ordenada en queryset ordenado manualmente
                preserved_order = models.Case(
                    *[models.When(id=id_h, then=pos) for pos, id_h in enumerate(ids_en_orden)]
                )

                qs = qs.filter(id__in=ids_en_orden).annotate(
                    distancia_m=models.Case(
                        *[
                            models.When(id=h.id, then=round(dist, 2))
                            for h, dist in cercanos
                        ],
                        default=None,
                        output_field=models.FloatField()
                    )
                ).order_by(preserved_order)

            except ValueError:
                pass  # lat/lon inválidos → se ignora distancia

        # Guardar en caché (queryset, NO lista)
        cache.set(cache_key, qs, 300)
        return qs

class MisReportesListView(ListAPIView):
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # El usuario pidió explícitamente que "Mis Reportes" sea SOLO para el que reporta el hueco inicialmente.
        return (
            Hueco.objects.filter(status=1, usuario=user)
            .distinct()
            .order_by("-fecha_reporte")
        )

class SeguidosListView(ListAPIView):
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Hueco.objects.filter(
                status=1,
                suscripciones__usuario=user,
                suscripciones__status=1,
            )
            .distinct()
            .order_by("-fecha_reporte")
        )
