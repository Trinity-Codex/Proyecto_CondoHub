"""Configuración de la app "gastos" (Django la registra al iniciar)."""
from django.apps import AppConfig


class GastosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Ruta completa de la app: todas las apps viven dentro de la carpeta "apps/".
    name = "apps.gastos"
    # Nombre con el que aparece la app en el panel de administración.
    verbose_name = "Gastos comunes"
