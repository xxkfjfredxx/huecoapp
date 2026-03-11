# 🕳️ HuecoApp – Backend API

¡Bienvenido al backend de **HuecoApp**!  
Este proyecto está construido con **Django** + **Django REST Framework** y maneja los reportes de daños viales, validaciones por usuarios, gamificación de reputación (puntos/niveles) y compresión automática de evidencias fotográficas.

---

## 📦 Tecnologías principales

- 🐍 **Python 3.10+** (Django 4.2+, DRF)
- 🗃️ **PostgreSQL / MySQL**
- ⚡ **Celery & Redis**: Para tareas en segundo plano (ej: procesamiento asíncrono de imágenes a WebP y conteo de vistas optimizado).
- 📲 **Firebase Admin SDK**: Notificaciones Push (FCM).
- 🔐 **JWT Authentication**: Manejado con `rest_framework_simplejwt`.

---

## 🚀 Cómo Iniciar el Servidor (Entorno de Desarrollo / Pruebas)

### 1. Activar Entorno Virtual y base de datos
Asegúrate de tener un servidor PostgreSQL ejecutándose y tu entorno virtual activo:
```bash
# Windows
.\venv\Scripts\activate
```

### 2. Levantar el caché de Redis (Vistas e Imágenes)
Usa Docker Compose para levantar la instancia aislada de Redis (`huecoapp_redis`).
```bash
docker-compose up -d
```

### 3. Ejecutar el Servidor Web (Django)
```bash
python manage.py runserver
python manage.py runserver 0.0.0.0:8000

```

### 4. Lanzar Workers de Celery (¡Importante para las vistas e imágenes!)
Abre **dos** nuevas pestañas en la terminal, activa el entorno virtual en ambas (`.\venv\Scripts\activate`) y corre:

**Terminal A (Worker para compresión de fotos):**
```bash
celery -A config worker -l info --pool=threads
```
**Terminal B (Beat para sincronizar las vistas de redis a BD):**
```bash
celery -A config beat -l info
```

*(Nota: En producción el proceso será muy similar, pero en lugar de `runserver`, se usará un servidor robusto como `gunicorn` o `daphne` atado a un proxy inverso con `Nginx`).*

> 🚨 **¡ATENCIÓN: DEUDA TÉCNICA PARA DESPLIEGUE A PRODUCCIÓN! (PostGIS)** 🚨
> 
> Actualmente la ubicación de los huecos (`latitud` / `longitud`) se guarda utilizando `FloatFields` básicos para facilitar el desarrollo rápido en el entorno local (Windows). 
> 
> **ANTES de desplegar y escalar la app en el servidor Linux de Producción, debes:**
> 1. Migrar la base de datos de PostgreSQL básico a **PostGIS** (`postgis/postgis:15-3.3-alpine` si usas Docker).
> 2. Transformar los campos `latitud/longitud` del modelo `Hueco` en un **`PointField`** de **GeoDjango**.
> 3. Instalar las dependencias del sistema en el server: `sudo apt-get install binutils libproj-dev gdal-bin`
> 
> Esto permitirá usar consultas espaciales nativas como `ST_DWithin`, lo cual es **obligatorio** para no colapsar la RAM del servidor tratando de buscar huecos cercanos usando algoritmos matemáticos en código cuando la base de datos supere los miles de registros.

---

## ⚙️ Instalación del proyecto en una nueva máquina (Windows)

### 1️⃣ Clona el repositorio
```bash
git clone https://github.com/xxkfjfredxx/sgr_backend.git
cd sgr_backend
```

### 2️⃣ Crea y activa el entorno virtual
```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Instala las dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4️⃣ Instala dependencias del sistema (si hace falta)

- Si falta `mysqlclient`:
```bash
pip install mysqlclient
```

- Si da error con `ImageField` (Pillow):
```bash
pip install Pillow
```

> ⚠️ **Importante (Windows):**  
> Si `mysqlclient` falla, asegúrate de tener:
> - ✅ **MySQL Server** instalado  
> - ✅ **MySQL Connector C**: https://dev.mysql.com/downloads/connector/c/  
> - ✅ **Microsoft C++ Build Tools**

---

### 5️⃣ Configura la base de datos

Abre el archivo `config/settings/development.py` y revisa la sección `DATABASES`:

```python
DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'sgr_db',
    'USER': 'root',
    'PASSWORD': 'tu_contraseña',
    'HOST': 'localhost',
    'PORT': '3306',
  }
}
```

---

### 6️⃣ Crea la base de datos (desde Workbench o CLI)

```sql
CREATE DATABASE sgr_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### 7️⃣ Aplica las migraciones
```bash
python manage.py migrate
```

---

### 8️⃣ (Opcional) Crea un superusuario
```bash
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```


---

### 9️⃣ Ejecuta el servidor
```bash
python manage.py runserver
# Opción A (recomendada)
python manage.py migrate
python manage.py migrate_schemas --executor=standard
```

Accede en tu navegador a: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

✅ **Listo para trabajar o continuar desarrollando tu sistema.**  
Para dudas o mejoras, crea un issue o contáctame.


el proyecto tambien tiene auth o2 celery y debug_toolbar y pip install django-ratelimit 

tambien se agrego encriptacion de campos
from encrypted_model_fields.fields import EncryptedCharField, EncryptedDecimalField
# Este campo se encriptará automáticamente
    employee_id_number = EncryptedCharField(max_length=20)
    
    # Este campo también se encriptará automáticamente
    salary = EncryptedDecimalField(max_digits=10, decimal_places=2)


from dotenv import load_dotenv
para almacenar claves en .env

"NAME": os.getenv("DB_NAME", "sgr_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "root"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),


Sentry : para monitoreo de errores de aplicaciones.
pip install bandit para ver vulnerabilidades

revisar 
OSSEC : Para detección de intrusiones.  ELK Stack (Elasticsearch, Logstash, Kibana),Popular APM Tools:
New Relic: Tracks response times, errors, and database queries.
Datadog: Provides monitoring for services, logs, and infrastructure.
Elastic APM: Integrates seamlessly with the ELK stack for centralized logging and monitoring.
Monitoring with Prometheus and Grafana
Kubernetes 
pip install pybreaker
Gremlin: Simulates attacks on your infrastructure.
Chaos Mesh: Runs chaos experiments in Kubernetes.
django-cachalot
django-silk
django-csp
django-defender


