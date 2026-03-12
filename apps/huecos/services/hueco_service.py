from geopy.distance import geodesic
from apps.huecos.models import Hueco, EstadoHueco

def get_huecos_cercanos(latitud, longitud, radio_metros=50):
    """
    Devuelve huecos cercanos según lat/lon y radio.
    Retorna lista de tuplas: (Hueco, distancia_en_metros)
    """
    huecos = Hueco.objects.filter(
        estado__in=[
            EstadoHueco.PENDIENTE, 
            EstadoHueco.ACTIVO, 
            EstadoHueco.REABIERTO, 
            EstadoHueco.CERRADO,
            EstadoHueco.EN_REPARACION,
            EstadoHueco.REPARADO
        ],
        status=1,
        is_deleted=False
    )
    cercanos = []
    for h in huecos:
        if not h.latitud or not h.longitud:
            continue
        distancia = geodesic((latitud, longitud), (h.latitud, h.longitud)).meters
        if distancia <= radio_metros:
            cercanos.append((h, distancia))
    return cercanos