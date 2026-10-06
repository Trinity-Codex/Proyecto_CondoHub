"""
Incidentes reportados por los residentes (RF07 y RF08).

RF07: el residente reporta un incidente con categoría y descripción.
RF08: el administrador (o el conserje) cambia su estado:
      recibido -> en proceso -> resuelto.
Cada cambio avisa por patrón Observer (RF10): al reportar se avisa a la
administración, y al cambiar de estado se avisa a quien lo reportó.
"""
from django.conf import settings
from django.db import models, transaction
from django.urls import reverse

from apps.condominios.models import Membresia
from apps.notificaciones.observador import Evento, Sujeto


class Incidente(Sujeto, models.Model):
    class Categoria(models.TextChoices):
        MANTENCION = "MANTENCION", "Mantención / reparación"
        SEGURIDAD = "SEGURIDAD", "Seguridad"
        RUIDOS = "RUIDOS", "Ruidos molestos"
        ASEO = "ASEO", "Aseo"
        AREAS_COMUNES = "AREAS_COMUNES", "Áreas comunes"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        RECIBIDO = "RECIBIDO", "Recibido"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        RESUELTO = "RESUELTO", "Resuelto"

    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="incidentes")
    unidad = models.ForeignKey(
        "condominios.Unidad", on_delete=models.SET_NULL, null=True, blank=True, related_name="incidentes",
        help_text="Unidad afectada (opcional).",
    )
    reportado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="incidentes")
    categoria = models.CharField("categoría", max_length=20, choices=Categoria.choices)
    titulo = models.CharField("título", max_length=120)
    descripcion = models.TextField("descripción")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.RECIBIDO)
    respuesta = models.TextField(blank=True, help_text="Comentario de la administración para el residente.")
    fecha_reporte = models.DateTimeField("fecha de reporte", auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_reporte"]

    def __str__(self):
        return f"#{self.pk} {self.titulo}"

    def get_absolute_url(self):
        return reverse("incidentes:detalle", args=[self.pk])

    @transaction.atomic
    def reportar(self):
        """RF07: guarda el incidente y avisa a la administración y al conserje."""
        self.save()
        responsables = [
            m.usuario
            for m in Membresia.objects.filter(
                condominio=self.condominio,
                rol__in=[Membresia.Rol.ADMINISTRADOR, Membresia.Rol.CONSERJE],
                activo=True,
            ).select_related("usuario")
        ]
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Nuevo incidente reportado",
                mensaje=f"{self.get_categoria_display()}: {self.titulo}",
                destinatarios=responsables,
                url=self.get_absolute_url(),
            )
        )

    @transaction.atomic
    def cambiar_estado(self, nuevo_estado, respuesta=""):
        """RF08: cambia el estado y avisa a quien reportó el incidente (RF10)."""
        self.estado = nuevo_estado
        if respuesta:
            self.respuesta = respuesta
        self.save(update_fields=["estado", "respuesta", "actualizado"])
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Tu incidente cambió de estado",
                mensaje=f"#{self.pk} {self.titulo}: {self.get_estado_display()}",
                destinatarios=[self.reportado_por],
                url=self.get_absolute_url(),
            )
        )
