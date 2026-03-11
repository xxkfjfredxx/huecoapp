from django.db import transaction 

@transaction.atomic
def registrar_puntos(usuario, cantidad, tipo, descripcion=""):
    """
    Registra puntos en el historial del usuario.
    El modelo PuntosUsuario.save (models.py:126) se encarga de 
    actualizar la reputación acumulada y el nivel de confianza.
    """
    from apps.huecos.models import PuntosUsuario  # evitar import circular

    return PuntosUsuario.objects.create(
        usuario=usuario,
        puntos=cantidad,
        tipo=tipo,
        descripcion=descripcion,
    )

def evaluar_validaciones_hueco(hueco):
    """
    Cede la responsabilidad a validacion_service para evitar duplicación.
    """
    from apps.huecos.services.validacion_service import evaluar_y_actualizar_estado_hueco
    evaluar_y_actualizar_estado_hueco(hueco)

def asignar_puntos_aprobacion(hueco):
    # Ya se maneja de forma unificada en el servicio
    pass

def asignar_puntos_rechazo(hueco):
    # Ya se maneja de forma unificada en el servicio
    pass
