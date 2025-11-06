from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db import models
from django.utils.timezone import now
from rest_framework.pagination import LimitOffsetPagination
from django.core.cache import cache

from .models import (
    Hueco, Confirmacion, Comentario,
    PuntosUsuario, HistorialHueco, ValidacionHueco
)
from .serializers import (
    HuecoSerializer, ConfirmacionSerializer,
    ComentarioSerializer, PuntosUsuarioSerializer,
    ValidacionHuecoSerializer
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
    queryset = Hueco.objects.all().order_by('-fecha_reporte')
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        user = self.request.user
        hoy = now().date()

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
                lat, lon = float(lat), float(lon)
                cercanos = get_huecos_cercanos(lat, lon, radio_metros=10)
                for h, distancia in cercanos:
                    if h.estado in ['cerrado', 'reabierto']:
                        hueco_existente = h
                        break
            except ValueError:
                pass

        # 3️⃣ Reapertura si corresponde
        if hueco_existente:
            hueco_existente.estado = 'reabierto'
            hueco_existente.numero_ciclos += 1
            hueco_existente.fecha_actualizacion = now()
            hueco_existente.save()

            HistorialHueco.objects.create(
                hueco=hueco_existente,
                usuario=user,
                accion=f"Hueco reabierto por {user.username}"
            )

            registrar_puntos(user, 5, "reapertura", f"Reapertura del hueco #{hueco_existente.id}")
            from apps.huecos.services.notificacion_service import notificar_reapertura
            
            notificar_reapertura(hueco_existente, user)

            return hueco_existente

        # 4️⃣ Crear nuevo hueco
        hueco = serializer.save(usuario=user)
        registrar_puntos(user, 10, "reporte", f"Nuevo reporte de hueco #{hueco.id}")

        HistorialHueco.objects.create(
            hueco=hueco,
            usuario=user,
            accion="Reporte de hueco creado"
        )

        return hueco


class ConfirmacionViewSet(viewsets.ModelViewSet):
    queryset = Confirmacion.objects.all().order_by('-fecha')
    serializer_class = ConfirmacionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        confirmacion = serializer.save(usuario=self.request.user)
        registrar_puntos(self.request.user, 2, "confirmacion", f"Confirmación del hueco #{confirmacion.hueco.id}")

        HistorialHueco.objects.create(
            hueco=confirmacion.hueco,
            usuario=self.request.user,
            accion="confirmado por usuario"
        )


class ComentarioViewSet(viewsets.ModelViewSet):
    queryset = Comentario.objects.all().order_by('-fecha')
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

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
        hueco = serializer.validated_data['hueco']
        voto = serializer.validated_data['voto']

        # Evitar validaciones repetidas
        if ValidacionHueco.objects.filter(hueco=hueco, usuario=usuario).exists():
            raise serializers.ValidationError("Ya has validado este hueco.")

        # Guardar validación
        validacion = serializer.save(usuario=usuario)

        # Procesar lógica desde el servicio
        procesar_validacion(hueco, usuario, voto)

        return validacion


class HuecosCercanosViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para listar huecos cercanos según ubicación y/o ciudad, con caché.
    Ejemplo:
      /api/huecos/cercanos/?lat=6.25&lon=-75.56&radio=1000&ciudad=Medellín
    """
    serializer_class = HuecoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        radio = float(self.request.query_params.get('radio', 1000))
        ciudad = self.request.query_params.get('ciudad')
        cache_key = f"huecos_{lat}_{lon}_{radio}_{ciudad}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        queryset = Hueco.objects.filter(
            estado__in=['activo', 'reabierto', 'pendiente_validacion']
        )

        if ciudad:
            queryset = queryset.filter(descripcion__icontains=ciudad)

        resultados = []
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                cercanos = get_huecos_cercanos(lat, lon, radio_metros=radio)
                resultados = [h for h, _ in cercanos]
                for h, distancia in cercanos:
                    h.distancia_m = round(distancia, 2)
                queryset = resultados
            except ValueError:
                pass
        else:
            queryset = queryset.order_by('-fecha_reporte')

        cache.set(cache_key, queryset, 300)
        return queryset
