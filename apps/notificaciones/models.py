"""Notificaciones dentro del sitio (RF10). Las crea el observador NotificadorEnSitio."""
from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField("título", max_length=150)
    mensaje = models.TextField()
    url = models.CharField("enlace", max_length=200, blank=True)
    leida = models.BooleanField("leída", default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-creada"]
        indexes = [models.Index(fields=["usuario", "leida"])]

    def __str__(self):
        return f"{self.titulo} -> {self.usuario}"


class RecordatorioEnviado(models.Model):
    """
    Constancia de un recordatorio de pago ya enviado (Issue #57): un aviso por cobro,
    persona y tipo. Así el comando enviar_recordatorios no repite avisos aunque corra
    varias veces el mismo día (ver recordatorios.py).
    """

    class Tipo(models.TextChoices):
        ANTES = "ANTES", "Antes del vencimiento"
        DESPUES = "DESPUES", "Después del vencimiento"

    cobro = models.ForeignKey("gastos.DetalleGastoComun", on_delete=models.CASCADE, related_name="recordatorios")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recordatorios")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    enviado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "recordatorio enviado"
        verbose_name_plural = "recordatorios enviados"
        constraints = [
            models.UniqueConstraint(fields=["cobro", "usuario", "tipo"], name="uq_recordatorio_cobro_usuario_tipo"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.cobro} -> {self.usuario}"
