"""Configuración de la app "rendicion": rendición de cuentas mensual a la comunidad (Ley 21.442) (Issue #55)."""
from django.apps import AppConfig


class RendicionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rendicion"  # con "apps." delante, como las demás apps
    verbose_name = "Rendición mensual"
