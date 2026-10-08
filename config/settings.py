"""
Configuración de CondoHub (plataforma de gestión de condominios).

Los valores que cambian de un PC a otro (clave de MySQL, modo DEBUG, etc.)
se leen del archivo ".env" que está en la raíz del proyecto. Cada integrante
crea el suyo copiando ".env.example" (el ".env" NO se sube a GitHub porque
contiene claves). Ver DOCUMENTACION.md, sección "Instalación".
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Carpeta raíz del proyecto (la que contiene manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables del archivo .env (si existe) como variables de entorno.
load_dotenv(BASE_DIR / ".env")


def _booleano(nombre, por_defecto):
    """Lee una variable de entorno como verdadero/falso ("1", "true", "si" -> True)."""
    valor = os.environ.get(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
# Clave para firmar sesiones y formularios. En producción debe ser secreta.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-condohub-solo-para-desarrollo")
# DEBUG=True: páginas de error detalladas (solo para desarrollo).
DEBUG = _booleano("DJANGO_DEBUG", True)
# Direcciones desde las que se acepta el servidor (separadas por coma en el .env).
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()
]

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps de CondoHub (carpeta apps/)
    "apps.core",            # diseño base, panel de inicio, condominio activo, permisos
    "apps.cuentas",         # usuarios (inicio de sesión)
    "apps.condominios",     # condominios, edificios, unidades, residentes y roles
    "apps.comunicados",     # comunicados oficiales (RF09)
    "apps.reservas",        # reservas de espacios comunes (RF05, RF06)
    "apps.incidentes",      # incidentes reportados por residentes (RF07, RF08)
    "apps.notificaciones",  # notificaciones dentro del sitio (RF10, patrón Observer)
    "apps.gastos",          # gastos comunes: períodos y egresos (RF02)
    "apps.proveedores",     # proveedores del condominio (RF: gestión de proveedores)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Propio: deja en request.condominio el condominio que el usuario está viendo.
    "apps.core.middleware.CondominioActivoMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Plantillas comunes a todo el sitio (base.html, inicio de sesión, etc.)
        "DIRS": [BASE_DIR / "templates"],
        # Además busca en <app>/templates/
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Propio: condominio activo, rol y notificaciones sin leer en todas las plantillas.
                "apps.core.context_processors.condohub",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de datos: MySQL 8
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "condohub"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        # 127.0.0.1 y no "localhost": en Windows "localhost" puede ir por IPv6.
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",  # tildes, ñ y emojis
            # Modo estricto: MySQL rechaza datos inválidos en vez de "arreglarlos".
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Solo para pruebas rápidas sin MySQL: USE_SQLITE=1 en el .env
if _booleano("USE_SQLITE", False):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# ---------------------------------------------------------------------------
# Usuarios e inicio de sesión
# ---------------------------------------------------------------------------
# Modelo de usuario propio (apps/cuentas/models.py). Debe definirse ANTES de la
# primera migración: cambiarlo después es muy difícil.
AUTH_USER_MODEL = "cuentas.Usuario"
LOGIN_URL = "cuentas:iniciar_sesion"
LOGIN_REDIRECT_URL = "core:inicio"
LOGOUT_REDIRECT_URL = "cuentas:iniciar_sesion"

import sys  # noqa: E402

# Durante las pruebas automáticas ("manage.py test") las claves se cifran con un
# algoritmo rápido: el real es lento A PROPÓSITO (dificulta adivinar claves) y
# haría que las pruebas, que crean muchos usuarios, tarden minutos.
if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Idioma y zona horaria
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos (CSS, JavaScript, imágenes propias)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Mensajes de Django (éxito, error...) con las clases de color de Bootstrap.
from django.contrib.messages import constants as mensajes  # noqa: E402

MESSAGE_TAGS = {mensajes.ERROR: "danger"}
