import os
from celery import Celery
# Establece el módulo de configuración de Django para el programa 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crea la instancia de la aplicación Celery
app = Celery('config')

# Carga la configuración de Celery desde el archivo de configuración de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre y carga las tareas automáticamente desde tus aplicaciones
app.autodiscover_tasks()
