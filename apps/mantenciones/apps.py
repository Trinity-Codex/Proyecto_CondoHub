"""Configuración de la app "mantenciones" (calendario de mantenciones periódicas del condominio)."""
from django.apps import AppConfig


class MantencionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mantenciones"  # con "apps." delante, como las demás apps
    verbose_name = "Mantenciones"

    def ready(self):
        """Suscribe los canales (campana y correo) a las alertas, como hace apps.notificaciones con sus sujetos."""
        from apps.notificaciones.observador import NotificadorCorreo, NotificadorEnSitio

        from .alertas import Alerta

        Alerta.suscribir(NotificadorEnSitio())
        Alerta.suscribir(NotificadorCorreo())
