# =========================
# Django settings (ordenado)
# =========================
from pathlib import Path
import os
from os import getenv
from datetime import timedelta

from dotenv import load_dotenv
from corsheaders.defaults import default_headers

# -------------------------
# Carga .env y banderas base
# -------------------------
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Cambia esto en tu .env => DEBUG=true/false
DEBUG = getenv("DEBUG", "true").lower() == "true"

SECRET_KEY = getenv("SECRET_KEY")
FIELD_ENCRYPTION_KEY = getenv("FIELD_ENCRYPTION_KEY")

# Hosts
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    # En prod, define ALLOWED_HOSTS=api.midominio.com,otra.com en .env
    ALLOWED_HOSTS = [h.strip() for h in getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Usuario custom
AUTH_USER_MODEL = "usuarios.User"

# Media
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# =========================
# Apps
# =========================
SHARED_APPS = [
    "jet.dashboard",
    "jet",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Terceros
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "oauth2_provider",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",

    # Tus apps
    "apps.utils",
    "apps.usuarios",
    "apps.huecos",
    # "apps.roles",  # déjalo comentado si no lo usas
]

INSTALLED_APPS = list(SHARED_APPS)

# Debug toolbar SOLO en dev
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

# =========================
# Middleware
# =========================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",              # CORS debe ir arriba
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Debug toolbar SOLO en dev
if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

# =========================
# URLS / WSGI / Templates
# =========================
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =========================
# Base de datos
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": getenv("DB_NAME", "huecoapp_db"),
        "USER": getenv("DB_USER", "postgres"),
        "PASSWORD": getenv("DB_PASSWORD", "root"),
        "HOST": getenv("DB_HOST", "localhost"),
        "PORT": getenv("DB_PORT", "5432"),
    }
}

# =========================
# DRF / Auth / Schema
# =========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.usuarios.auth.VersionedJWTAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ] + (["rest_framework.authentication.SessionAuthentication"] if DEBUG else []),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.utils.permissions.CSRFDobleSubmitMutations",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(getenv("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": getenv("JWT_ROTATE_REFRESH", "true").lower() == "true",
    "BLACKLIST_AFTER_ROTATION": getenv("JWT_BLACKLIST_AFTER_ROTATION", "true").lower() == "true",
    "UPDATE_LAST_LOGIN": True,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",  # para desarrollo
        "LOCATION": "unique-huecos-cache"
    }
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SGR API",
    "DESCRIPTION": "Documentación de la API",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],  # doc pública
    "SERVE_AUTHENTICATION": [],                                     # sin auth en doc
    "GROUP_BY_URL": True,
}

# =========================
# CORS / CSRF por entorno
# =========================
# Credenciales (cookies) habilitadas en ambos; el origen decide
CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    # Define en .env: CORS_ALLOWED_ORIGINS=https://app.midominio.com,https://admin.midominio.com
    CORS_ALLOWED_ORIGINS = [o.strip() for o in getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    # CSRF de navegador: orígenes confiables
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Headers permitidos
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-requested-with",
    "x-csrf-token",
    "x-csrftoken",
    "x-active-company",
]

# (Opcional) Exponer algunos headers al browser (no afecta cookies)
CORS_EXPOSE_HEADERS = ["content-length", "content-type"]

# =========================
# Seguridad producción
# =========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"

# =========================
# Sentry (opcional)
# =========================
SENTRY_DSN = getenv("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=True)

# =========================
# i18n / zona horaria
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================
# Static / default PK
# =========================
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# Jet Admin
# =========================
JET_DEFAULT_THEME = "light-gray"
JET_DASHBOARD_SITE_TITLE = "Panel de Administración"
JET_INDEX_DASHBOARD = "jet.dashboard.dashboard.DefaultIndexDashboard"
JET_APP_INDEX_DASHBOARD = "jet.dashboard.dashboard.DefaultAppIndexDashboard"
