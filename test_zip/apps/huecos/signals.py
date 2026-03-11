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

    # Si el hueco fue rechazado, penalizamos al creador
    if hueco.estado == "rechazado":
        creador = hueco.usuario
        registrar_puntos(creador, -10, "reporte_falso", f"Hueco #{hueco.id} rechazado por falsedad")
        if hasattr(creador, 'reputacion'):
            creador.reputacion.puntaje_total -= 15
            creador.reputacion.actualizar_nivel()
