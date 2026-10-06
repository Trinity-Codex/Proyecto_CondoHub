"""Configuración de la app "core" (Django la registra al iniciar)."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Ruta completa de la app: todas las apps viven dentro de la carpeta "apps/".
    name = "apps.core"
    # Nombre con el que aparece la app en el panel de administración.
    verbose_name = "Núcleo del sitio"
