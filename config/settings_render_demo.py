"""
Demo visual pública en Render (Issue #111): solo lectura y datos ficticios.

Hereda la demo local (SQLite en .demo_cliente/ y fecha de referencia) y agrega lo que exige
publicarla por HTTPS. El entorno habitual (config.settings con MySQL) no cambia.
Variables por nombre: DJANGO_SECRET_KEY (panel de Render) y RENDER_EXTERNAL_HOSTNAME (la
define Render). Si falta una o no es válida, el arranque se detiene antes de tocar la base.
"""
import os
import re

from django.core.exceptions import ImproperlyConfigured

# Mismo patrón que settings_demo: Django hereda la configuración completa y aquí se reemplaza.
from .settings_demo import *  # noqa: F403
from .settings_demo import BASE_DIR, MIDDLEWARE

DEBUG = False

# La clave firma sesiones y CSRF: nunca la de desarrollo ni una corta (check --deploy W009).
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5
        or SECRET_KEY.startswith("django-insecure")):
    raise ImproperlyConfigured(
        "Define DJANGO_SECRET_KEY en el panel de Render: al menos 50 caracteres variados "
        "y distinta de la clave de desarrollo."
    )

# Render publica el dominio en RENDER_EXTERNAL_HOSTNAME. Se exige un nombre DNS simple, en
# minúsculas, sin comodines, puertos ni rutas: es el único host aceptado.
_ETIQUETA_DNS = re.compile(r"[a-z\d](?:[a-z\d-]{0,61}[a-z\d])?")
HOST_DEMO = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
_etiquetas = HOST_DEMO.split(".")
if len(HOST_DEMO) > 253 or len(_etiquetas) < 2 or not all(_ETIQUETA_DNS.fullmatch(e) for e in _etiquetas):
    raise ImproperlyConfigured(
        "RENDER_EXTERNAL_HOSTNAME debe ser el dominio de Render, ej. mi-demo.onrender.com."
    )

ALLOWED_HOSTS = [HOST_DEMO]
CSRF_TRUSTED_ORIGINS = [f"https://{HOST_DEMO}"]
SITIO_URL = f"https://{HOST_DEMO}"

# Render termina TLS en su proxy y avisa con X-Forwarded-Proto: sin esto Django creería que
# todo llega por HTTP y la redirección a HTTPS entraría en bucle.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS corto y solo para este host: el dominio onrender.com es compartido, así que no se
# declaran subdominios ni precarga (check --deploy avisa W005 y W021 por eso, a propósito).
SECURE_HSTS_SECONDS = 3600

# Sin correo real: la demo no envía invitaciones ni recuperaciones de clave.
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# Estáticos recolectados al arrancar (collectstatic) y servidos por WhiteNoise con DEBUG=False.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# WhiteNoise justo después de SecurityMiddleware (lo pide su documentación). La solo lectura
# va al final: decide con la ruta resuelta, después de CSRF, sesión y condominio activo.
MIDDLEWARE = [
    *MIDDLEWARE[:1],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
    "apps.core.middleware_demo.SoloLecturaDemoMiddleware",
]

# Errores a la salida estándar: Render los muestra en Logs sin guardar archivos.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "WARNING"},
}
