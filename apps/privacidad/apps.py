"""Configuración de la app "privacidad": aviso de privacidad y derechos sobre los datos personales (Issue #51)."""
from django.apps import AppConfig


class PrivacidadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.privacidad"  # con "apps." delante, como las demás apps
    verbose_name = "Privacidad"
