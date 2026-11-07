"""Configuración de la app "auditoria": registro de quién hizo qué y cuándo (Ley 21.719) (Issue #27)."""
from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"  # con "apps." delante, como las demás apps
    verbose_name = "Auditoría"
