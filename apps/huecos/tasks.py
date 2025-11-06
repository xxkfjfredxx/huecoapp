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
