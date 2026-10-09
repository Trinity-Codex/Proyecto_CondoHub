"""Configuración de la app "pagos" (estado de cuenta y pagos de los residentes)."""
from django.apps import AppConfig


class PagosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pagos"  # con "apps." delante, como las demás apps
    verbose_name = "Pagos"