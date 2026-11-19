"""
Incidentes reportados por los residentes (RF07 y RF08).

RF07: el residente reporta un incidente con categoría y descripción.
RF08: el administrador (o el conserje) cambia su estado:
      recibido -> en proceso -> resuelto.
Cada cambio avisa por patrón Observer (RF10): al reportar se avisa a la
administración, y al cambiar de estado se avisa a quien lo reportó.
"""
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse

from apps.auditoria.servicios import Accion, registrar
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
    def cambiar_estado(self, nuevo_estado, respuesta="", *, usuario=None):
        """
        RF08: cambia el estado y avisa a quien reportó el incidente (RF10).

        Auditoría (#27): se registra el cambio real en la misma transacción.
        Si no hay un usuario, el registro identifica al sistema.
        """
        # Se bloquea la fila para auditar el estado anterior real, incluso con cambios simultáneos.
        anterior = Incidente.objects.select_for_update().values_list("estado", flat=True).get(pk=self.pk)
        self.estado = nuevo_estado
        if respuesta:
            self.respuesta = respuesta
        self.save(update_fields=["estado", "respuesta", "actualizado"])
        if anterior != nuevo_estado:
            registrar(
                usuario, self.condominio, Accion.MODIFICAR, self,
                antes={"estado": anterior}, despues={"estado": nuevo_estado},
            )
        self.notificar(
            Evento(
                condominio=self.condominio,
                titulo="Tu incidente cambió de estado",
                mensaje=f"#{self.pk} {self.titulo}: {self.get_estado_display()}",
                destinatarios=[self.reportado_por],
                url=self.get_absolute_url(),
            )
        )


def ruta_foto(instancia, nombre_original):
    """
    Dónde se guarda cada foto: incidentes/<condominio_id>/<uuid>.<ext>.
    El nombre lo genera el servidor y no el usuario: así nadie adivina la ruta ni
    cuela «../» o un nombre con datos personales (la foto además solo se sirve por la vista protegida).
    """
    extension = Path(nombre_original).suffix.lower()
    return f"incidentes/{instancia.incidente.condominio_id}/{uuid.uuid4().hex}{extension}"


# Límite de fotos por incidente (Issue #122; el cliente debe confirmarlo). Vive aquí, y no en forms.py,
# porque la regla la aplica el servicio FotoIncidente.subir() y el formulario solo avisa antes.
MAX_FOTOS_POR_INCIDENTE = 10
MENSAJE_SIN_MEDIA = "La subida de fotos aún no está habilitada en este servidor."


def mensaje_cupo(existentes, nuevas):
    """Mismo texto para el aviso del formulario y para el rechazo del servicio."""
    return (
        f"Cada incidente admite hasta {MAX_FOTOS_POR_INCIDENTE} fotos: este ya tiene {existentes} "
        f"y quieres agregar {nuevas}."
    )


class SubidaNoPermitida(Exception):
    """El servicio se niega a guardar fotos (subida apagada o sobre el cupo); el mensaje es apto para mostrarlo."""


class FotoIncidente(models.Model):
    """
    Foto de respaldo de un incidente (Issue #122): «antes» la sube quien lo reporta y
    «después» la sube la administración o el conserje al gestionarlo o resolverlo.
    No tiene campo `condominio` propio: llega a él por el incidente (`incidente__condominio`).
    """

    class Etapa(models.TextChoices):
        ANTES = "ANTES", "Antes"
        DESPUES = "DESPUES", "Después"

    incidente = models.ForeignKey(Incidente, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to=ruta_foto)
    etapa = models.CharField(max_length=10, choices=Etapa.choices)
    fecha_subida = models.DateTimeField("fecha de subida", auto_now_add=True)
    # SET_NULL: si se borra al usuario, la evidencia del incidente se conserva.
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="fotos_incidentes"
    )

    class Meta:
        ordering = ["fecha_subida", "pk"]

    def __str__(self):
        return f"Foto {self.get_etapa_display().lower()} del incidente #{self.incidente_id}"

    @classmethod
    def subir(cls, incidente, archivos, etapa, usuario):
        """
        Guarda las fotos y registra cada subida en auditoría, todo en una transacción.
        Las reglas viven aquí y no en el formulario, para que ningún llamador pueda saltárselas:
        con la subida apagada o sobre el cupo se lanza SubidaNoPermitida antes de escribir nada.
        """
        # @spec:incidentes-fotos-de-respaldo
        if not archivos:
            return []  # reportar sin fotos no debe depender de la subida
        if not settings.FOTOS_INCIDENTES_HABILITADAS:
            # Sin almacenamiento persistente decidido (#29) las fotos se perderían al reiniciar el servidor.
            raise SubidaNoPermitida(MENSAJE_SIN_MEDIA)
        escritos = []  # (almacenamiento, nombre) de lo ya escrito en disco
        try:
            with transaction.atomic():
                # Se bloquea el incidente: dos subidas simultáneas cuentan el cupo una después de la otra.
                Incidente.objects.select_for_update().get(pk=incidente.pk)
                existentes = cls.objects.filter(incidente=incidente).count()
                if existentes + len(archivos) > MAX_FOTOS_POR_INCIDENTE:
                    raise SubidaNoPermitida(mensaje_cupo(existentes, len(archivos)))
                fotos = []
                for archivo in archivos:
                    foto = cls(incidente=incidente, etapa=etapa, subido_por=usuario)
                    # El archivo se escribe aquí (no al insertar) para anotar su nombre aunque falle la fila.
                    foto.imagen.save(archivo.name, archivo, save=False)
                    escritos.append((foto.imagen.storage, foto.imagen.name))
                    foto.save()
                    registrar(
                        usuario, incidente.condominio, Accion.CREAR, foto,
                        despues={"incidente": incidente.pk, "etapa": etapa},
                    )
                    fotos.append(foto)
        except Exception:
            # La transacción se revirtió pero el disco no: se borran los archivos ya escritos.
            for almacenamiento, nombre in escritos:
                almacenamiento.delete(nombre)
            raise
        return fotos

    @transaction.atomic
    def eliminar(self, usuario):
        # @spec:incidentes-fotos-de-respaldo
        """
        Borra la foto y deja la baja en auditoría. Se audita ANTES de borrar (después el pk queda en None).
        Django no borra el archivo con la fila: se quita del disco solo si la transacción se confirma,
        para no perder la imagen de una baja que luego se deshace.
        """
        registrar(
            usuario, self.incidente.condominio, Accion.ELIMINAR, self,
            antes={"incidente": self.incidente_id, "etapa": self.etapa},
        )
        archivo = self.imagen
        self.delete()
        transaction.on_commit(lambda: archivo.storage.delete(archivo.name))
