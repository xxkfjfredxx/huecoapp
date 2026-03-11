from celery import shared_task
from firebase_admin import messaging

@shared_task
def enviar_notificaciones_push(tokens, titulo, mensaje):
    """
    Envía notificaciones push a una lista de tokens FCM.
    Ejecutado de forma asíncrona por Celery.
    """
    if not tokens:
        return

    # Firebase permite enviar de a 500 tokens por lote
    chunk_size = 500
    for i in range(0, len(tokens), chunk_size):
        lote = tokens[i:i + chunk_size]
        messages = [
            messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=mensaje
                ),
                token=token
            )
            for token in lote
        ]

        try:
            response = messaging.send_all(messages)
            print(f"[FCM] {response.success_count} enviadas, {response.failure_count} fallidas.")
        except Exception as e:
            print(f"[FCM ERROR] {e}")

@shared_task
def optimizar_imagen_hueco_task(hueco_id):
    from apps.huecos.models import Hueco
    from django.core.files.base import ContentFile
    from io import BytesIO
    from PIL import Image
    
    try:
        hueco = Hueco.objects.get(id=hueco_id)
        if not hueco.imagen:
            return
            
        original_file = hueco.imagen.file
        original_file.seek(0)
        try:
            img = Image.open(original_file)
        except Exception:
            return
            
        DETALLE_SIZE = (1080, 1080)
        PREVIEW_SIZE = (300, 300)
        QUALITY = 75
        
        img_detalle = img.copy()
        if img_detalle.width > DETALLE_SIZE[0] or img_detalle.height > DETALLE_SIZE[1]:
            img_detalle.thumbnail(DETALLE_SIZE)
            
        buffer_detalle = BytesIO()
        img_detalle.save(buffer_detalle, format='WEBP', quality=QUALITY)
        hueco.imagen.save(f'{hueco.pk}_detalle.webp', ContentFile(buffer_detalle.getvalue()), save=False)
        
        img_preview = img.copy()
        img_preview.thumbnail(PREVIEW_SIZE)
        
        thumb_io = BytesIO()
        img_preview.save(thumb_io, format='WEBP', quality=QUALITY)
        
        thumb_filename = f'{hueco.pk}_preview.webp'
        hueco.imagen_preview.save(thumb_filename, ContentFile(thumb_io.getvalue()), save=False)
        
        hueco.save(update_fields=['imagen', 'imagen_preview'])
    except Exception as e:
        print(f"[CELERY ERROR] Optimizando imagen de hueco {hueco_id}: {e}")

@shared_task
def sincronizar_vistas_redis():
    """
    Sincroniza las vistas cacheadas en Redis hacia la Base de Datos.
    Idealmente ejecutado cada 5-10 minutos vía Celery Beat.
    """
    from django.core.cache import cache
    from apps.huecos.models import Hueco
    import redis
    from django.conf import settings
    from django.db.models import F
    
    try:
        # Obtenemos el cliente subyacente de redis si está disponible
        r = redis.Redis.from_url(settings.CACHES['default']['LOCATION'] if 'redis' in str(settings.CACHES['default'].get('BACKEND', '')) else 'redis://localhost:6379/1')
        keys = r.keys("hueco_vistas_*")
        
        for key_bytes in keys:
            key = key_bytes.decode('utf-8')
            hueco_id_str = key.split('_')[-1]
            if hueco_id_str.isdigit():
                vistas = int(r.get(key) or 0)
                if vistas > 0:
                    Hueco.objects.filter(id=hueco_id_str).update(vistas=F('vistas') + vistas)
                    r.set(key, 0) # reiniciar contador
    except Exception as e:
        print(f"[CELERY ERROR] Sincronizando vistas: {e}")
