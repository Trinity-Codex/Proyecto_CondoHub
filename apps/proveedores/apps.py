"""Configuración de la app "proveedores" (gestión de proveedores del condominio)."""
from django.apps import AppConfig


class ProveedoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proveedores"  # con "apps." delante, como las demás apps
    verbose_name = "Proveedores"