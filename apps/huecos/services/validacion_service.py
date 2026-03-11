from apps.huecos.models import PuntosUsuario, HistorialHueco, EstadoHueco
from apps.usuarios.models import ReputacionUsuario
from apps.huecos.services.puntos_service import registrar_puntos
from django.db import models, transaction

def procesar_validacion(hueco, usuario, voto):
    """
    Registra el voto de un usuario sobre la existencia de un hueco.
    Calcula el peso del voto según reputación y actualiza estadísticas.
    """
    with transaction.atomic():
        # 0. Evitar que el autor valide su propio reporte (doble validación)
        if hueco.usuario == usuario:
            return

        # 1. Obtener reputación del validador para determinar peso
        reputacion, _ = ReputacionUsuario.objects.get_or_create(usuario=usuario)
        if reputacion.nivel_confianza == "experto":
            peso = 2
        elif reputacion.nivel_confianza == "confiable":
            peso = 1.5
        else:
            peso = 1

        # 2. Actualizar conteos ponderados en el hueco
        if voto:
            hueco.validaciones_positivas += peso
            # Puntos para el validador
            registrar_puntos(usuario, 2, "confirmacion", f"Confirmación positiva de hueco #{hueco.id}")
        else:
            hueco.validaciones_negativas += peso
            # Puntos para el validador
            registrar_puntos(usuario, 1, "confirmacion", f"Validación negativa de hueco #{hueco.id}")
        
        hueco.save(update_fields=['validaciones_positivas', 'validaciones_negativas'])

        # 3. Registrar en historial
        HistorialHueco.objects.create(
            hueco=hueco,
            usuario=usuario,
            accion=f"Validación {'positiva' if voto else 'negativa'} (Peso: {peso})"
        )

        # 4. Evaluar si el hueco cambia de estado (PENDIENTE -> ACTIVO/RECHAZADO)
        evaluar_y_actualizar_estado_hueco(hueco)

def evaluar_y_actualizar_estado_hueco(hueco):
    """
    Revisa si un hueco en estado PENDIENTE debe ser aprobado o rechazado
    basándose en los umbrales de validación.
    """
    from apps.huecos.config import UMBRAL_VALIDACION_POSITIVA, UMBRAL_VALIDACION_NEGATIVA
    from apps.huecos.services.notificacion_service import notificar_validacion_final
    
    if hueco.estado != EstadoHueco.PENDIENTE:
        return

    positivas = hueco.validaciones_positivas
    negativas = hueco.validaciones_negativas
    autor = hueco.usuario

    if positivas >= UMBRAL_VALIDACION_POSITIVA:
        hueco.estado = EstadoHueco.ACTIVO
        hueco.save(update_fields=['estado'])
        
        # Premiar al autor del reporte real
        registrar_puntos(autor, 10, "verificacion", f"Hueco #{hueco.id} verificado por la comunidad")
        
        # Premiar (bono extra) a los validadores que acertaron
        for v in hueco.validaciones.filter(voto=True):
            if v.usuario != autor:
                registrar_puntos(v.usuario, 3, "confirmacion", f"Bono por validación correcta de hueco #{hueco.id}")
        
        # Notificar al autor
        notificar_validacion_final(hueco, es_positivo=True)

    elif negativas >= UMBRAL_VALIDACION_NEGATIVA:
        hueco.estado = EstadoHueco.RECHAZADO
        hueco.save(update_fields=['estado'])
        
        # Penalizar al autor del reporte falso
        registrar_puntos(autor, -15, "reporte_falso", f"Hueco #{hueco.id} rechazado como falso")
        
        # Premiar a los validadores que detectaron la falsedad
        for v in hueco.validaciones.filter(voto=False):
            if v.usuario != autor:
                registrar_puntos(v.usuario, 2, "confirmacion", f"Bono por detectar reporte falso #{hueco.id}")
        
        # Notificar al autor
        notificar_validacion_final(hueco, es_positivo=False)
