"""
Comunicados oficiales del condominio (RF09).

Un comunicado es GENERAL (para todo el condominio) o POR EDIFICIO. Al
publicarlo se notifica a los residentes que corresponda (RF10) usando el
patrón Observer: Comunicado es un "Sujeto" (ver apps/notificaciones/observador.py).

Vigencia y lectura (Issue #58, RF13):
  - vigente_hasta: opcional. Desde el día siguiente el comunicado está vencido y sale
    de la lista principal y del panel de inicio (sigue en "Ver vencidos").
  - LecturaComunicado: el residente lo marca como leído. El administrador ve el conteo
    POR UNIDAD (confirmaciones()): una unidad confirma si cualquiera de sus residentes leyó.
"""
from django.conf import settings
from django.db import models, transaction
from django.urls import reverse

from apps.condominios.models import Membresia, Residente, Unidad
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

    def vigentes(self, hoy):
        """Sin fecha de vigencia, o hasta hoy inclusive (Issue #58)."""
        return self.filter(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=hoy))

    def vencidos(self, hoy):
        """Con la fecha "Visible hasta" ya pasada."""
        return self.filter(vigente_hasta__lt=hoy)


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
    # Issue #58: el día indicado todavía se ve; desde el siguiente está vencido.
    vigente_hasta = models.DateField("visible hasta", null=True, blank=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", auto_now_add=True)

    # Manager con los métodos de ComunicadoQuerySet (ej. Comunicado.objects.visibles_para(...)).
    objects = ComunicadoQuerySet.as_manager()

    class Meta:
        ordering = ["-fijado", "-fecha_publicacion"]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("comunicados:detalle", args=[self.pk])

    def esta_vencido(self, hoy):
        return self.vigente_hasta is not None and self.vigente_hasta < hoy

    def unidades_destinatarias(self):
        """
        Unidades a las que va el comunicado y que tienen al menos un residente activo
        (el mismo criterio que destinatarios()). Base del conteo de lectura (Issue #58).
        """
        unidades = Unidad.objects.filter(edificio__condominio=self.condominio, residentes__activo=True)
        if self.tipo == self.Tipo.POR_EDIFICIO and self.edificio_id:
            unidades = unidades.filter(edificio=self.edificio)
        return unidades.distinct()

    def confirmaciones(self):
        """
        (confirmadas, destinatarias): conjuntos de unidades. Una unidad confirma si cualquiera
        de sus residentes activos marcó el comunicado como leído: el conteo es por unidad.
        """
        destinatarias = set(self.unidades_destinatarias().select_related("edificio"))
        lectores = self.lecturas.values("usuario")
        confirmadas = set(
            self.unidades_destinatarias().filter(residentes__activo=True, residentes__usuario__in=lectores)
            .select_related("edificio")
        )
        return confirmadas, destinatarias

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


class LecturaComunicado(models.Model):
    """
    Un residente marcó el comunicado como leído (Issue #58). Se guarda la persona, no la
    unidad: cada residente ve su propio estado y el conteo por unidad se calcula al
    mostrarlo (Comunicado.confirmaciones()).
    """

    comunicado = models.ForeignKey(Comunicado, on_delete=models.CASCADE, related_name="lecturas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comunicados_leidos")
    leido = models.DateTimeField("leído", auto_now_add=True)

    class Meta:
        verbose_name = "lectura de comunicado"
        verbose_name_plural = "lecturas de comunicados"
        constraints = [models.UniqueConstraint(fields=["comunicado", "usuario"], name="uq_lectura_comunicado_usuario")]

    def __str__(self):
        return f"{self.usuario} leyó «{self.comunicado}»"
