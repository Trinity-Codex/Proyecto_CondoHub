"""Configuración de la app "notificaciones" (Django la registra al iniciar)."""
from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Ruta completa de la app: todas las apps viven dentro de la carpeta "apps/".
    name = "apps.notificaciones"
    # Nombre con el que aparece la app en el panel de administración.
    verbose_name = "Notificaciones"

    def ready(self):
        """
        ready() se ejecuta una vez, cuando Django termina de cargar las apps.
        Aquí se SUSCRIBEN los observadores a los sujetos (patrón Observer).
        Para un canal nuevo (ej. correo), basta con agregar otra línea aquí.
        """
        from apps.comunicados.models import Comunicado
        from apps.gastos.models import PeriodoGasto
        from apps.incidentes.models import Incidente
        from apps.pagos.models import Pago
        from apps.privacidad.models import SolicitudTitular

        from .observador import NotificadorCorreo, NotificadorEnSitio
        from .recordatorios import Recordatorio

        notificador = NotificadorEnSitio()
        Comunicado.suscribir(notificador)
        Incidente.suscribir(notificador)
        PeriodoGasto.suscribir(notificador)  # gastos comunes emitidos (Issue #2)
        Pago.suscribir(notificador)  # pago registrado (Issue #4)
        SolicitudTitular.suscribir(notificador)  # solicitudes de datos personales (Issue #51)
        Recordatorio.suscribir(notificador)  # recordatorios de pago (Issue #57)

        # Canal nuevo: correo electrónico (Issue #14). Solo se agregan estas
        # líneas; comunicados, incidentes, gastos y pagos no se modifican.
        correo = NotificadorCorreo()
        Comunicado.suscribir(correo)
        Incidente.suscribir(correo)
        PeriodoGasto.suscribir(correo)
        Pago.suscribir(correo)
        SolicitudTitular.suscribir(correo)
        Recordatorio.suscribir(correo)
