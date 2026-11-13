"""
Solicitudes del titular de datos personales (Issue #51, Ley 21.719).

Una persona pide acceso, rectificación, supresión u oposición sobre sus datos en su
condominio activo: el responsable del tratamiento es la administración de cada
condominio, por eso la solicitud le pertenece a él. El administrador la responde y la
cierra en un solo paso. Ciclo: PENDIENTE -> CERRADA (con respuesta y fecha).

Es un "Sujeto" del patrón Observer: avisa a los administradores al llegar y a la
persona al cerrarse, por la campana y por correo (ver apps/notificaciones/apps.py).
"""
from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.servicios import Accion, registrar
from apps.condominios.models import Membresia
from apps.notificaciones.observador import Evento, Sujeto


class SolicitudTitular(Sujeto, models.Model):
    class Tipo(models.TextChoices):
        ACCESO = "ACCESO", "Acceso: saber qué datos míos se tratan"
        RECTIFICACION = "RECTIFICACION", "Rectificación: corregir un dato"
        SUPRESION = "SUPRESION", "Supresión: eliminar un dato"
        OPOSICION = "OPOSICION", "Oposición: que no se use un dato para algún fin"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CERRADA = "CERRADA", "Cerrada"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitudes_titular")
    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="solicitudes_titular")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    detalle = models.TextField(help_text="Cuéntanos qué dato y qué necesitas, para responderte mejor.")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.TextField(blank=True)
    creada = models.DateTimeField(auto_now_add=True)
    cerrada = models.DateTimeField(null=True, blank=True)
    cerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitudes_cerradas"
    )

    class Meta:
        verbose_name = "solicitud del titular"
        verbose_name_plural = "solicitudes del titular"
        ordering = ["-creada"]

    def __str__(self):
        return f"#{self.pk} {self.tipo_corto} de {self.usuario}"

    def get_absolute_url(self):
        return reverse("privacidad:solicitud", args=[self.pk])

    @property
    def tipo_corto(self):
        """"Acceso", "Rectificación"...: la etiqueta sin la explicación que va después de ":"."""
        return self.get_tipo_display().partition(":")[0]

    @property
    def esta_pendiente(self):
        return self.estado == self.Estado.PENDIENTE

    @transaction.atomic
    def presentar(self):
        """Guarda la solicitud y avisa a los administradores del condominio."""
        self.save()
        # Auditoría (#27): sin el detalle, que puede traer datos personales.
        registrar(self.usuario, self.condominio, Accion.CREAR, self, despues={"tipo": self.tipo, "estado": self.estado})
        administradores = [
            m.usuario
            for m in Membresia.objects.filter(
                condominio=self.condominio, rol=Membresia.Rol.ADMINISTRADOR, activo=True
            ).select_related("usuario")
        ]
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Nueva solicitud de datos personales",
                mensaje=f"{self.tipo_corto} de {self.usuario}.",
                destinatarios=administradores,
                url=reverse("privacidad:responder", args=[self.pk]),
            )
        )

    @transaction.atomic
    def cerrar(self, respuesta, por):
        """Responde y cierra la solicitud, y avisa a la persona. Una cerrada no se vuelve a cerrar."""
        # Se bloquea la fila y se lee su estado real: si dos administradores responden a
        # la vez, el segundo espera al primero, la encuentra cerrada y no la sobrescribe.
        self.estado = type(self).objects.select_for_update().values_list("estado", flat=True).get(pk=self.pk)
        if not self.esta_pendiente:
            raise ValueError("La solicitud ya está cerrada.")
        self.respuesta = respuesta
        self.estado = self.Estado.CERRADA
        self.cerrada = timezone.now()
        self.cerrada_por = por
        self.save(update_fields=["respuesta", "estado", "cerrada", "cerrada_por"])
        registrar(  # auditoría (#27): sin la respuesta, que puede traer datos personales
            por, self.condominio, Accion.MODIFICAR, self,
            antes={"estado": self.Estado.PENDIENTE}, despues={"estado": self.estado},
        )
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Respondimos tu solicitud de datos personales",
                mensaje=f"{self.tipo_corto}: ya está la respuesta de la administración.",
                destinatarios=[self.usuario],
                url=self.get_absolute_url(),
            )
        )
