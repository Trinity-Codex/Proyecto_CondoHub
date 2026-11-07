"""Configuración de la app "cartera": deuda por antigüedad y unidades morosas (Issue #54)."""
from django.apps import AppConfig


class CarteraConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cartera"  # con "apps." delante, como las demás apps
    verbose_name = "Cartera"
