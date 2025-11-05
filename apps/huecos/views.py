from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated,AllowAny
from django.db.models import Q
from django.db import models
from geopy.distance import geodesic
from django.utils.timezone import now, timedelta
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
from apps.usuarios.models import ReputacionUsuario

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

        # 🔹 1. Verificar límite diario
        reportes_hoy = Hueco.objects.filter(usuario=user, fecha_reporte__date=hoy).count()
        if reportes_hoy >= 20:
            raise serializers.ValidationError("Límite diario de 20 reportes alcanzado.")

        # 🔹 2. Verificar si existe un hueco cerrado cercano
        lat = self.request.data.get('latitud')
        lon = self.request.data.get('longitud')
        hueco_existente = None

        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                for h in Hueco.objects.filter(estado__in=['cerrado', 'reabierto']):
                    distancia = geodesic((h.latitud, h.longitud), (lat, lon)).meters
                    if distancia < 10:  # Distancia en metros
                        hueco_existente = h
                        break
            except ValueError:
                pass

        # 🔹 3. Si se encontró hueco cerrado → reabrir
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

            PuntosUsuario.objects.create(
                usuario=user,
                tipo="reapertura",
                puntos=5,
                descripcion=f"Reapertura del hueco #{hueco_existente.id}"
            )

            return hueco_existente

        # 🔹 4. Si no existe → crear hueco nuevo
        hueco = serializer.save(usuario=user)

        PuntosUsuario.objects.create(
            usuario=user,
            tipo="reporte",
            puntos=10,
            descripcion=f"Nuevo reporte de hueco #{hueco.id}"
        )

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

        # Puntos por confirmar
        PuntosUsuario.objects.create(
            usuario=self.request.user,
            tipo="confirmacion",
            puntos=2,
            descripcion=f"Confirmación del hueco #{confirmacion.hueco.id}"
        )

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

        PuntosUsuario.objects.create(
            usuario=self.request.user,
            tipo="comentario",
            puntos=1,
            descripcion=f"Comentario en hueco #{comentario.hueco.id}"
        )


class PuntosUsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """Permite listar los puntos y ver el ranking general"""
    queryset = PuntosUsuario.objects.all().order_by('-fecha')
    serializer_class = PuntosUsuarioSerializer

    def list(self, request, *args, **kwargs):
        # Ranking resumido de usuarios
        ranking = (
            PuntosUsuario.objects.values('usuario__username')
            .annotate(total=models.Sum('puntos'))
            .order_by('-total')
        )
        return Response(ranking)


class ValidacionHuecoViewSet(viewsets.ModelViewSet):
    """
    Los usuarios validan si un hueco realmente existe o no.
    - Se pondera el voto según la reputación del usuario.
    - Se evalúan los resultados acumulados.
    - Se asignan puntos a todos los involucrados.
    """
    queryset = ValidacionHueco.objects.all()
    serializer_class = ValidacionHuecoSerializer
    

    def perform_create(self, serializer):
        usuario = self.request.user
        hueco = serializer.validated_data['hueco']
        voto = serializer.validated_data['voto']

        # Evitar que un usuario valide el mismo hueco más de una vez
        if ValidacionHueco.objects.filter(hueco=hueco, usuario=usuario).exists():
            raise serializers.ValidationError("Ya has validado este hueco.")

        # Guardar validación
        validacion = serializer.save(usuario=usuario)

        # Obtener reputación y peso
        reputacion, _ = ReputacionUsuario.objects.get_or_create(usuario=usuario)
        if reputacion.nivel_confianza == "experto":
            peso = 2
        elif reputacion.nivel_confianza == "confiable":
            peso = 1.5
        else:
            peso = 1

        # Actualizar conteos ponderados en el hueco
        if voto:
            hueco.validaciones_positivas += peso
        else:
            hueco.validaciones_negativas += peso
        hueco.save()

        # Registrar acción en historial
        HistorialHueco.objects.create(
            hueco=hueco,
            usuario=usuario,
            accion=f"Validación {'positiva' if voto else 'negativa'} de {usuario.username}"
        )

        # Recalcular estado del hueco según validaciones
        self._evaluar_estado_hueco(hueco, voto, usuario)

        return validacion

    def _evaluar_estado_hueco(self, hueco, voto, validador):
        """
        Aplica la lógica de reputación y puntos cuando un hueco alcanza
        el umbral de validaciones positivas o negativas.
        """
        positivas = hueco.validaciones_positivas
        negativas = hueco.validaciones_negativas
        autor = hueco.usuario

        if positivas >= 5 and hueco.estado == "pendiente_validacion":
            hueco.estado = "activo"
            hueco.save()

            # Premiar autor y validadores positivos
            PuntosUsuario.objects.create(
                usuario=autor,
                tipo="verificacion",
                puntos=10,
                descripcion=f"Hueco #{hueco.id} verificado como real"
            )

            for v in hueco.validaciones.filter(voto=True):
                PuntosUsuario.objects.create(
                    usuario=v.usuario,
                    tipo="confirmacion",
                    puntos=5,
                    descripcion=f"Validación positiva del hueco #{hueco.id}"
                )

        elif negativas >= 3 and hueco.estado == "pendiente_validacion":
            hueco.estado = "rechazado"
            hueco.save()

            # Penalizar autor, premiar validadores negativos
            PuntosUsuario.objects.create(
                usuario=autor,
                tipo="verificacion",
                puntos=-15,
                descripcion=f"Hueco #{hueco.id} rechazado (falso reporte)"
            )

            for v in hueco.validaciones.filter(voto=False):
                PuntosUsuario.objects.create(
                    usuario=v.usuario,
                    tipo="confirmacion",
                    puntos=3,
                    descripcion=f"Validación negativa del hueco #{hueco.id}"
                )

        # Actualizar reputaciones de todos los usuarios involucrados
        for v in hueco.validaciones.all():
            reputacion, _ = ReputacionUsuario.objects.get_or_create(usuario=v.usuario)
            total = PuntosUsuario.objects.filter(usuario=v.usuario).aggregate(total=models.Sum('puntos'))['total'] or 0
            reputacion.puntaje_total = total
            reputacion.actualizar_nivel()

        # Actualizar reputación del autor también
        rep_autor, _ = ReputacionUsuario.objects.get_or_create(usuario=autor)
        total_autor = PuntosUsuario.objects.filter(usuario=autor).aggregate(total=models.Sum('puntos'))['total'] or 0
        rep_autor.puntaje_total = total_autor
        rep_autor.actualizar_nivel()


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
        # 🔹 1. Parámetros de búsqueda
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        radio = float(self.request.query_params.get('radio', 1000))  # metros
        ciudad = self.request.query_params.get('ciudad')
        cache_key = f"huecos_{lat}_{lon}_{radio}_{ciudad}"

        # 🔹 2. Buscar en caché primero
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        # 🔹 3. Base de búsqueda: huecos activos o reabiertos
        queryset = Hueco.objects.filter(
            estado__in=['activo', 'reabierto', 'pendiente_validacion']
        )

        # 🔹 4. Filtro por ciudad
        if ciudad:
            queryset = queryset.filter(descripcion__icontains=ciudad)

        resultados = []
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                for h in queryset:
                    distancia = geodesic((lat, lon), (h.latitud, h.longitud)).meters
                    if distancia <= radio:
                        h.distancia_m = round(distancia, 2)
                        resultados.append(h)
                resultados.sort(key=lambda x: x.distancia_m)
                queryset = resultados
            except ValueError:
                pass

        else:
            queryset = queryset.order_by('-fecha_reporte')

        # 🔹 5. Guardar en caché por 5 minutos (300 seg)
        cache.set(cache_key, queryset, 300)

        return queryset