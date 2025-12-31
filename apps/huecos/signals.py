from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ValidacionHueco, Hueco
from usuarios.models import  ReputacionUsuario
from apps.huecos.services.puntos_service import registrar_puntos

@receiver(post_save, sender=ValidacionHueco)
def actualizar_estado_hueco(sender, instance, created, **kwargs):
    if not created:
        return

    hueco = instance.hueco
    usuario = instance.usuario
    reputacion = getattr(usuario, 'reputacion', None)

    # Si el usuario tiene buena reputación, su voto cuenta doble
    peso = 2 if reputacion and reputacion.nivel_confianza == "experto" else 1

    # Actualizar contadores del hueco
    if instance.confirmacion:
        hueco.validaciones_positivas += peso
        registrar_puntos(usuario, 2, "validacion_positiva", f"Confirmó existencia de hueco #{hueco.id}")
        reputacion.puntaje_total += 1
    else:
        hueco.validaciones_negativas += peso
        registrar_puntos(usuario, 1, "validacion_negativa", f"Negó existencia de hueco #{hueco.id}")
        reputacion.puntaje_total += 1

    hueco.save()
    if reputacion:
        reputacion.actualizar_nivel()

    # Re-evaluar si el hueco cambia de estado
    hueco.evaluar_validaciones()

    if hueco.estado == "rechazado":
        creador = hueco.usuario
        registrar_puntos(creador, -10, "reporte_falso", f"Hueco #{hueco.id} rechazado por falsedad")
        if hasattr(creador, 'reputacion'):
            creador.reputacion.puntaje_total -= 15
            creador.reputacion.actualizar_nivel()


from .models import Confirmacion, HistorialHueco
from .config import UMBRAL_CONFIRMACION_REPARADO

@receiver(post_save, sender=Confirmacion)
def procesar_confirmacion_estado(sender, instance, created, **kwargs):
    """
    Automatiza el cambio de estado a 'reparado' si suficientes usuarios lo confirman.
    """
    if not created:
        return

    hueco = instance.hueco
    
    # Solo procesamos si el hueco está activo o reabierto
    if hueco.estado not in ['activo', 'reabierto']:
        return

    # Contar votos de "ya está reparado" (confirmado=False)
    # y votos de "sigue ahí" (confirmado=True)
    votos_reparado = Confirmacion.objects.filter(hueco=hueco, confirmado=False).count()
    votos_sigue_ahi = Confirmacion.objects.filter(hueco=hueco, confirmado=True).count()

    # Umbral desde config
    if votos_reparado >= UMBRAL_CONFIRMACION_REPARADO:
        hueco.estado = 'reparado'
        hueco.save()
        
        # Registrar historial
        HistorialHueco.objects.create(
            hueco=hueco,
            usuario=instance.usuario,  # El usuario que completó el umbral
            accion="Marcado como reparado por la comunidad"
        )
        # Notificar al creador original (opcional, implementar luego)

    # Nota: Podrías agregar lógica inversa (si muchos dicen que sigue ahí, reabrirlo si estaba en duda)

