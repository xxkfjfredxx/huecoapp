from django.db.models import Q
from django.conf import settings
from apps.huecos.models import DispositivoUsuario
from apps.usuarios.models import User
from apps.huecos.tasks import enviar_notificaciones_push

def get_tokens_para_notificar(usuarios):
    """Obtiene los tokens FCM de los usuarios especificados"""
    return list(
        DispositivoUsuario.objects.filter(usuario__in=usuarios)
        .values_list('token_fcm', flat=True)
    )

def notificar_reapertura(hueco, usuario_reapertor):
    """
    Envía notificación push a todos los usuarios que han participado en el hueco
    excepto el que lo reabrió.
    """
    participantes = User.objects.filter(
        Q(comentarios__hueco=hueco) |
        Q(validaciones__hueco=hueco) |
        Q(confirmaciones__hueco=hueco) |
        Q(suscripciones__hueco=hueco, suscripciones__status=1) # Seguidores
    ).exclude(id=usuario_reapertor.id).distinct()

    tokens = get_tokens_para_notificar(participantes)
    if tokens:
        titulo = "Hueco reabierto 🚧"
        mensaje = f"El hueco #{hueco.id} ha sido reabierto cerca de tu ubicación o es uno que sigues."
        try:
            enviar_notificaciones_push.delay(tokens, titulo, mensaje)
        except Exception as e:
            print(f"Error al enviar notificación de reapertura: {e}")

def notificar_cambio_estado(hueco, nuevo_estado_nombre, excluidos=[]):
    """
    Notifica a reporteros y seguidores sobre un cambio de estado (ej: Reparado).
    """
    participantes = User.objects.filter(
        Q(id=hueco.usuario.id) | # Autor
        Q(suscripciones__hueco=hueco, suscripciones__status=1) | # Seguidores
        Q(comentarios__hueco=hueco)
    ).exclude(id__in=excluidos).distinct()

    tokens = get_tokens_para_notificar(participantes)
    if tokens:
        titulo = f"Actualización: {nuevo_estado_nombre}✅"
        mensaje = f"El hueco #{hueco.id} ahora está en estado '{nuevo_estado_nombre}'."
        try:
            enviar_notificaciones_push.delay(tokens, titulo, mensaje)
        except Exception as e:
            print(f"Error al enviar notificación de cambio de estado: {e}")

def notificar_validacion_final(hueco, es_positivo):
    """
    Notifica al autor si su hueco fue aprobado o rechazado por la comunidad.
    """
    tokens = get_tokens_para_notificar([hueco.usuario])
    if tokens:
        if es_positivo:
            titulo = "¡Reporte validado! 🎉"
            mensaje = f"Tu reporte del hueco #{hueco.id} ha sido validado por la comunidad. ¡Ganaste puntos!"
        else:
            titulo = "Reporte rechazado"
            mensaje = f"Lamentablemente tu reporte #{hueco.id} fue marcado como falso o inexistente."
        
        try:
            enviar_notificaciones_push.delay(tokens, titulo, mensaje)
        except Exception as e:
            print(f"Error al enviar notificación de validación: {e}")
