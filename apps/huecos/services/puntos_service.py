from django.db import transaction

@transaction.atomic
def registrar_puntos(usuario, cantidad, tipo, descripcion):
    """
    Crea registro de puntos y actualiza reputación total de forma atómica.
    """
    from apps.huecos.models import PuntosUsuario  # import local para evitar ciclo

    PuntosUsuario.objects.create(
        usuario=usuario,
        puntos=cantidad,
        tipo=tipo,
        descripcion=descripcion,
    )

    usuario.reputacion_total = (usuario.reputacion_total or 0) + cantidad
    usuario.save(update_fields=["reputacion_total"])
