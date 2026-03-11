from django.db import transaction 

@transaction.atomic
def registrar_puntos(usuario, cantidad, tipo, descripcion=""):
    """
    Registra puntos y deja que el modelo PuntosUsuario actualice la reputación
    automáticamente en ReputacionUsuario.
    """
    from apps.huecos.models import PuntosUsuario  # evitar import circular

    return PuntosUsuario.objects.create(
        usuario=usuario,
        puntos=cantidad,
        tipo=tipo,
        descripcion=descripcion,
    )
