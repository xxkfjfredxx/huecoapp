import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/1")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL