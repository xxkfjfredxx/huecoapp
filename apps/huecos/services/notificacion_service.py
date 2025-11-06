from django.db.models import Q
from django.conf import settings
from apps.huecos.models import DispositivoUsuario
from apps.usuarios.models import User
from apps.huecos.tasks import enviar_notificaciones_push

def notificar_reapertura(hueco, usuario_reapertor):
    """
    Envía notificación push a todos los usuarios que han participado en el hueco
    (comentado, validado o confirmado) excepto el que lo reabrió.
    """
    participantes = User.objects.filter(
        Q(comentarios__hueco=hueco) |
        Q(validaciones__hueco=hueco) |
        Q(confirmaciones__hueco=hueco)
    ).exclude(id=usuario_reapertor.id).distinct()

    if not participantes.exists():
        return

    tokens = list(
        DispositivoUsuario.objects.filter(usuario__in=participantes)
        .values_list('token_fcm', flat=True)
    )

    if not tokens:
        return

    titulo = "Hueco reabierto 🚧"
    mensaje = f"El hueco #{hueco.id} que validaste o comentaste ha sido reabierto. ¡Ayuda confirmando si sigue presente!"

    # Enviar tarea asíncrona con Celery
    enviar_notificaciones_push.delay(tokens, titulo, mensaje)
