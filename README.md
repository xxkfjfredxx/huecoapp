# 🛡️ Sistema de Gestión de Riesgos – Backend

¡Bienvenido al backend del **Sistema de Gestión de Riesgos Laborales**!  
Este proyecto está construido con **Django** + **Django REST Framework**, y forma parte de una solución integral para la gestión de empleados, documentos y riesgos laborales en organizaciones.

---

## 📦 Tecnologías utilizadas

- 🐍 **Python 3.10+**
- 🌐 **Django** y **Django REST Framework**
- 🗂️ Modularización profesional por apps (`apps/`)
- 🔐 **JWT Authentication**
- 🗃️ **MariaDB / MySQL compatible**
- 📂 Gestión de documentos con `FileField` y estructura organizada por tipo/fecha

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


