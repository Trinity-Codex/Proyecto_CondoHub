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
