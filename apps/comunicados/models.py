"""
Comunicados oficiales del condominio (RF09).

Un comunicado es GENERAL (para todo el condominio) o POR EDIFICIO. Al
publicarlo se notifica a los residentes que corresponda (RF10) usando el
patrón Observer: Comunicado es un "Sujeto" (ver apps/notificaciones/observador.py).
"""
from django.conf import settings
from django.db import models, transaction
from django.urls import reverse

from apps.condominios.models import Membresia, Residente
from apps.notificaciones.observador import Evento, Sujeto


class ComunicadoQuerySet(models.QuerySet):
    """Consultas reutilizables de comunicados (se usan con Comunicado.objects.<método>)."""

    def visibles_para(self, usuario, condominio, ve_todos):
        """
        Comunicados que un usuario puede ver en un condominio. Es la ÚNICA regla
        de visibilidad: la usan la lista, el detalle y el panel de inicio.
          - ve_todos=True (administrador, comité, conserje): todos los del condominio.
          - residente: los generales y los dirigidos a los edificios donde vive.
        """
        qs = self.filter(condominio=condominio)
        if ve_todos:
            return qs
        mis_edificios = usuario.residencias.filter(activo=True).values("unidad__edificio")
        return qs.filter(models.Q(tipo=Comunicado.Tipo.GENERAL) | models.Q(edificio__in=mis_edificios))


class Comunicado(Sujeto, models.Model):
    class Tipo(models.TextChoices):
        GENERAL = "GENERAL", "General (todo el condominio)"
        POR_EDIFICIO = "POR_EDIFICIO", "Solo un edificio"

    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="comunicados")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comunicados")
    titulo = models.CharField("título", max_length=150)
    contenido = models.TextField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.GENERAL)
    # Solo se usa si tipo = POR_EDIFICIO.
    edificio = models.ForeignKey(
        "condominios.Edificio", on_delete=models.CASCADE, null=True, blank=True, related_name="comunicados"
    )
    fijado = models.BooleanField(default=False, help_text="Los fijados aparecen primero.")
    fecha_publicacion = models.DateTimeField("fecha de publicación", auto_now_add=True)

    # Manager con los métodos de ComunicadoQuerySet (ej. Comunicado.objects.visibles_para(...)).
    objects = ComunicadoQuerySet.as_manager()

    class Meta:
        ordering = ["-fijado", "-fecha_publicacion"]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("comunicados:detalle", args=[self.pk])

    def destinatarios(self):
        """Usuarios que deben recibir el comunicado: residentes del condominio o del edificio."""
        residentes = Residente.objects.filter(activo=True, unidad__edificio__condominio=self.condominio)
        if self.tipo == self.Tipo.POR_EDIFICIO and self.edificio_id:
            residentes = residentes.filter(unidad__edificio=self.edificio)
        usuarios = {r.usuario for r in residentes.select_related("usuario")}
        # El comité también recibe todos los comunicados.
        usuarios |= {
            m.usuario
            for m in Membresia.objects.filter(
                condominio=self.condominio, rol=Membresia.Rol.COMITE, activo=True
            ).select_related("usuario")
        }
        usuarios.discard(self.autor)  # el autor no se notifica a sí mismo
        return list(usuarios)

    @transaction.atomic
    def publicar(self):
        """Guarda el comunicado y avisa a los observadores (RF09 + RF10)."""
        self.save()
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Nuevo comunicado",
                mensaje=self.titulo,
                destinatarios=self.destinatarios(),
                url=self.get_absolute_url(),
            )
        )
