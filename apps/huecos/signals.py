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


from .models import Confirmacion, HistorialHueco, EstadoHueco
from .config import UMBRAL_CONFIRMACION_REPARADO

@receiver(post_save, sender=Confirmacion)
def procesar_confirmacion_estado(sender, instance, created, **kwargs):
    """
    Automatiza el cambio de estado si suficientes usuarios votan por un estado específico.
    Lógica: Si el estado votado alcanza el umbral, el hueco cambia a ese estado.
    """
    if not created:
        return

    hueco = instance.hueco
    voto_estado = instance.nuevo_estado # Integer

    # Si el estado es nulo o igual al actual, ignorar
    if not voto_estado or voto_estado == hueco.estado:
        return

    # Contar votos para este estado específico EN EL CICLO ACTUAL
    count = Confirmacion.objects.filter(
        hueco=hueco, 
        nuevo_estado=voto_estado,
        numero_ciclo=hueco.numero_ciclos  # Filtro clave
    ).count()

    # Umbral
    if count >= UMBRAL_CONFIRMACION_REPARADO:
        hueco.estado = voto_estado
        hueco.save()
        
        # Obtener nombre del estado para el historial
        nombre_estado = EstadoHueco(voto_estado).label
        
        HistorialHueco.objects.create(
            hueco=hueco,
            usuario=instance.usuario,
            accion=f"Cambio a '{nombre_estado}' por votación de la comunidad"
        )

        # --- Repartir Puntos por Aprobación ---
        # Buscar todos los que votaron por este estado EN EL CICLO ACTUAL
        ganadores = Confirmacion.objects.filter(
            hueco=hueco,
            nuevo_estado=voto_estado,
            numero_ciclo=hueco.numero_ciclos
        )
        for ganador in ganadores:
            registrar_puntos(
                ganador.usuario, 
                5, # Puntos por acertar
                "confirmacion_exitosa", 
                f"Tu voto ayudó a cambiar el hueco #{hueco.id} a {nombre_estado}"
            )

