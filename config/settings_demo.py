"""Demo local con datos ficticios, separada de las bases habituales."""
from datetime import date

# Django hereda la configuración completa; solo se reemplaza el entorno local de demo.
from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".demo_cliente" / "demo.sqlite3",
    }
}
DEMO_FECHA_REFERENCIA = date(2026, 11, 16)
ALLOWED_HOSTS = ["127.0.0.1"]
SITIO_URL = "http://127.0.0.1:8016"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Los puertos de localhost comparten cookies; la demo conserva una sesión propia.
SESSION_COOKIE_NAME = "condohub_demo_sessionid"
CSRF_COOKIE_NAME = "condohub_demo_csrftoken"
