from geopy.distance import geodesic
from apps.huecos.models import Hueco

def get_huecos_cercanos(latitud, longitud, radio_metros=50):
    """
    Devuelve huecos cercanos según lat/lon y radio.
    Retorna lista de tuplas: (Hueco, distancia_en_metros)
    """
    huecos = Hueco.objects.filter(
        estado__in=['pendiente_validacion', 'cerrado', 'reabierto', 'activo'],
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