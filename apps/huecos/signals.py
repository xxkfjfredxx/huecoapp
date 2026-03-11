from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ValidacionHueco, Hueco
from usuarios.models import  ReputacionUsuario
from apps.huecos.services.puntos_service import registrar_puntos

@receiver(post_save, sender=ValidacionHueco)
def actualizar_estado_hueco(sender, instance, created, **kwargs):
    if not created:
        return

    # Usar el servicio unificado para procesar la validación y evitar duplicados
    from apps.huecos.services.validacion_service import procesar_validacion
    procesar_validacion(instance.hueco, instance.usuario, instance.voto)


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

        # Notificar a los interesados
        from apps.huecos.services.notificacion_service import notificar_cambio_estado
        notificar_cambio_estado(hueco, nombre_estado)

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

