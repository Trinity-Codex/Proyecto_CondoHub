"""
Mantenciones periódicas del condominio (Issue #123, RQ-08) y sus ejecuciones.

El administrador carga las mantenciones que define el condominio (extintores, red húmeda, ascensores...)
con su frecuencia en meses. Esta app no afirma qué es obligatorio por ley: eso lo decide el cliente.
"""
import calendar
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.auditoria.servicios import Accion, registrar



def ruta_certificado(instancia, nombre):
    """`upload_to` del certificado: nombre al azar y solo la extensión que ya fijó el validador (jpg, png o pdf)."""
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    extension = extension if extension in ("jpg", "png", "pdf") else "bin"
    return f"mantenciones/certificados/{uuid.uuid4().hex}.{extension}"


# Anticipación por defecto con la que una mantención pasa a «por vencer».
ANTICIPACION_POR_DEFECTO = 15


# @spec:mantenciones-calendario-de-mantenciones
def sumar_meses(fecha, meses):
    """
    Suma meses de calendario a una fecha. Si el mes de llegada no tiene ese día, queda el último día del mes:
    31-ene + 1 mes = 28 o 29-feb; 29-feb-2028 + 12 meses = 28-feb-2029.
    Se hace a mano porque `dateutil` no está en requirements.txt (y `timedelta` no sabe de meses).
    """
    indice = fecha.year * 12 + (fecha.month - 1) + meses  # meses contados desde el año 0
    anio, mes_base_cero = divmod(indice, 12)
    mes = mes_base_cero + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


class Mantencion(models.Model):
    class Estado(models.TextChoices):
        # Estas claves NO se guardan: el estado se calcula con la fecha de hoy (ver estado_en).
        AL_DIA = "AL_DIA", "Al día"
        POR_VENCER = "POR_VENCER", "Por vencer"
        VENCIDA = "VENCIDA", "Vencida"

    # REGLA MULTI-CONDOMINIO: cada mantención pertenece a un solo condominio.
    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="mantenciones")
    nombre = models.CharField("mantención", max_length=120, help_text="Ej.: Recarga de extintores.")
    # Tope de 120 meses (10 años): evita fechas imposibles y errores de digitación.
    frecuencia_meses = models.PositiveSmallIntegerField(
        "frecuencia (meses)", validators=[MinValueValidator(1), MaxValueValidator(120)],
    )
    proxima_fecha = models.DateField("próxima fecha")
    # Si el proveedor se borra, la mantención sigue existiendo (normalmente se desactiva, no se borra).
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True, related_name="mantenciones",
    )
    dias_anticipacion = models.PositiveSmallIntegerField(
        "anticipación de la alerta (días)", default=ANTICIPACION_POR_DEFECTO,
        validators=[MaxValueValidator(365)],
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["proxima_fecha", "nombre"]
        verbose_name = "mantención"
        verbose_name_plural = "mantenciones"

    def __str__(self):
        return self.nombre

    # @spec:mantenciones-calendario-de-mantenciones
    def estado_en(self, hoy):
        """
        Estado respecto de `hoy`. Vencida: la fecha ya pasó. Por vencer: faltan `dias_anticipacion` días o menos
        (el mismo día cuenta como por vencer: aún se puede hacer hoy). Al día: el resto.
        """
        if self.proxima_fecha < hoy:
            return self.Estado.VENCIDA
        if self.proxima_fecha <= hoy + timedelta(days=self.dias_anticipacion):
            return self.Estado.POR_VENCER
        return self.Estado.AL_DIA

    @property
    def estado(self):
        """El estado hoy, con la fecha local de Chile (no la UTC del servidor)."""
        return self.estado_en(timezone.localdate())

    # @spec:mantenciones-calendario-de-mantenciones
    def registrar_ejecucion(self, usuario, fecha, observacion="", certificado=None):
        """
        Anota que la mantención se hizo en `fecha` y recalcula la próxima: fecha + frecuencia_meses.
        Se parte de la fecha en que se HIZO (no de la que tocaba): así una mantención atrasada no se «pone al día»
        sola ni se acumulan fechas ya pasadas. Todo va en una transacción con su registro de auditoría.
        """
        with transaction.atomic():
            anterior = self.proxima_fecha
            ejecucion = EjecucionMantencion.objects.create(
                mantencion=self, fecha=fecha, observacion=observacion, usuario=usuario, certificado=certificado or "",
            )
            self.proxima_fecha = sumar_meses(fecha, self.frecuencia_meses)
            self.save(update_fields=["proxima_fecha"])
            registrar(
                usuario, self.condominio, Accion.CREAR, ejecucion,
                antes={"proxima_fecha": anterior.isoformat()},
                despues={
                    "fecha_ejecucion": fecha.isoformat(), "proxima_fecha": self.proxima_fecha.isoformat(),
                    "con_certificado": bool(certificado),
                },
            )
        return ejecucion


class EjecucionMantencion(models.Model):
    """Cada vez que se hizo una mantención. Se conserva el historial: no se edita la próxima fecha a mano."""

    mantencion = models.ForeignKey(Mantencion, on_delete=models.CASCADE, related_name="ejecuciones")
    fecha = models.DateField("fecha en que se hizo")
    observacion = models.TextField("observación", max_length=500, blank=True)
    # La cuenta puede borrarse más adelante: la ejecución queda sin autor, pero no se pierde.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
    )
    # Certificado o foto (JPG, PNG o PDF, máx. 5 MB). No se publica por MEDIA_URL: lo entrega CertificadoView con permisos.
    certificado = models.FileField(upload_to=ruta_certificado, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "ejecución de mantención"
        verbose_name_plural = "ejecuciones de mantención"

    def __str__(self):
        return f"{self.mantencion} · {self.fecha:%d-%m-%Y}"


class AlertaEnviada(models.Model):
    """
    Constancia de que ya se avisó de una mantención para una fecha de vencimiento (Issue #123). Un aviso por
    mantención y por ciclo: al registrar una ejecución la fecha cambia y el ciclo siguiente puede avisar de nuevo.
    La restricción única hace idempotente al comando aunque corra varias veces el mismo día.
    """

    mantencion = models.ForeignKey(Mantencion, on_delete=models.CASCADE, related_name="alertas")
    fecha_objetivo = models.DateField("fecha de vencimiento avisada")
    enviada = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mantencion", "fecha_objetivo"], name="una_alerta_por_ciclo")]
