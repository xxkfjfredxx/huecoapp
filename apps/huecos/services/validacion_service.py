from apps.huecos.models import PuntosUsuario, HistorialHueco
from apps.usuarios.models import ReputacionUsuario
from apps.huecos.services.puntos_service import registrar_puntos
from django.db import models

def procesar_validacion(hueco, usuario, voto):
    """
    Evalúa el estado del hueco según votos y reputaciones.
    Lógica movida desde ValidacionHuecoViewSet.
    """

    # Obtener reputación del validador
    reputacion, _ = ReputacionUsuario.objects.get_or_create(usuario=usuario)
    if reputacion.nivel_confianza == "experto":
        peso = 2
    elif reputacion.nivel_confianza == "confiable":
        peso = 1.5
    else:
        peso = 1

    # Actualizar conteos ponderados
    if voto:
        hueco.validaciones_positivas += peso
    else:
        hueco.validaciones_negativas += peso
    hueco.save()

    # Registrar acción
    HistorialHueco.objects.create(
        hueco=hueco,
        usuario=usuario,
        accion=f"Validación {'positiva' if voto else 'negativa'} de {usuario.username}"
    )

    # Umbrales desde config
    from apps.huecos.config import UMBRAL_VALIDACION_POSITIVA, UMBRAL_VALIDACION_NEGATIVA

    positivas = hueco.validaciones_positivas
    negativas = hueco.validaciones_negativas
    autor = hueco.usuario

    if positivas >= UMBRAL_VALIDACION_POSITIVA and hueco.estado == "pendiente_validacion":
        hueco.estado = "activo"
        hueco.save()

        registrar_puntos(autor, 10, "verificacion", f"Hueco #{hueco.id} verificado como real")
        for v in hueco.validaciones.filter(voto=True):
            registrar_puntos(v.usuario, 5, "confirmacion", f"Validación positiva del hueco #{hueco.id}")

    elif negativas >= UMBRAL_VALIDACION_NEGATIVA and hueco.estado == "pendiente_validacion":
        hueco.estado = "rechazado"
        hueco.save()

        registrar_puntos(autor, -15, "verificacion", f"Hueco #{hueco.id} rechazado (falso reporte)")
        for v in hueco.validaciones.filter(voto=False):
            registrar_puntos(v.usuario, 3, "confirmacion", f"Validación negativa del hueco #{hueco.id}")

    # Actualizar reputaciones de todos los usuarios involucrados
    for v in hueco.validaciones.all():
        rep, _ = ReputacionUsuario.objects.get_or_create(usuario=v.usuario)
        total = PuntosUsuario.objects.filter(usuario=v.usuario).aggregate(total=models.Sum('puntos'))['total'] or 0
        rep.puntaje_total = total
        rep.actualizar_nivel()

    # Actualizar reputación del autor
    rep_autor, _ = ReputacionUsuario.objects.get_or_create(usuario=autor)
    total_autor = PuntosUsuario.objects.filter(usuario=autor).aggregate(total=models.Sum('puntos'))['total'] or 0
    rep_autor.puntaje_total = total_autor
    rep_autor.actualizar_nivel()
