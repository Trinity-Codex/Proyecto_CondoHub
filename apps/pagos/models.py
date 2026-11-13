"""
Modelos de la app "pagos".

El estado de cuenta (Issue #3) lee los cobros de apps/gastos (DetalleGastoComun).
Aquí vive Pago (Issue #4, RF04): cada abono que el administrador registra contra un cobro.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.servicios import Accion, registrar
from apps.condominios.models import Residente
from apps.core.formato import formatear_monto
from apps.condominios.residencias import cobros_visibles
from apps.gastos.models import DetalleGastoComun
from apps.notificaciones.observador import Evento, Sujeto


class PagoQuerySet(models.QuerySet):
    def vigentes(self):
        """
        Contrato C4 (#53): solo los pagos no anulados. Toda suma de lo pagado parte de aquí,
        para que un pago anulado no rebaje la deuda en ningún reporte ni en "Mi cuenta".
        """
        return self.filter(anulado=False)


class Pago(Sujeto, models.Model):
    """
    Un pago (total o parcial) de un cobro de gastos comunes.

    Hereda de Sujeto (patrón Observer, igual que Incidente): al registrarse avisa
    a los residentes de la unidad sin saber cómo se les avisa (campana, correo...).
    El nombre related_name="pagos" está acordado con Walther: sus reportes (#5)
    suman "pagos__monto".
    """

    class Medio(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        EFECTIVO = "EFECTIVO", "Efectivo"
        CHEQUE = "CHEQUE", "Cheque"
        WEBPAY = "WEBPAY", "Webpay"

    detalle = models.ForeignKey(DetalleGastoComun, on_delete=models.CASCADE, related_name="pagos")
    fecha = models.DateField(default=timezone.localdate)
    # Pesos enteros (como el resto de los montos). Mínimo 1: no existen pagos de $0.
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    medio = models.CharField(max_length=15, choices=Medio.choices, default=Medio.TRANSFERENCIA)
    observacion = models.CharField(max_length=200, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_registrados"
    )
    creado = models.DateTimeField(auto_now_add=True)
    # Anulación (#53): el pago no se borra, para que el cierre mensual y la auditoría
    # muestren qué se corrigió, quién lo hizo y por qué.
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.CharField(max_length=200, blank=True)
    anulado_en = models.DateTimeField(null=True, blank=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_anulados"
    )

    # Manager por defecto que sigue devolviendo TODOS los pagos (el admin y la huella de la
    # demo los cuentan todos); las sumas piden Pago.objects.vigentes() explícitamente.
    objects = PagoQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self):
        return f"Pago ${self.monto} de {self.detalle}"

    @property
    def condominio(self):
        return self.detalle.periodo.condominio

    # @spec:pagos-registro-de-pagos
    @classmethod
    @transaction.atomic
    def registrar(cls, detalle, monto, fecha=None, medio=Medio.TRANSFERENCIA, observacion="", registrado_por=None):
        """
        Registra un pago sobre un cobro. Todo ocurre en UNA transacción:

        1. select_for_update() bloquea la fila del cobro: si dos personas registran
           un pago al mismo tiempo, la segunda espera y ve el saldo ya actualizado
           (así nunca se paga de más por una carrera entre dos clics).
        2. No se acepta más que el saldo pendiente (calculado solo con pagos vigentes, #53).
        3. Si con este pago se alcanza el total, el cobro pasa a PAGADO.
        4. Se avisa a los residentes de la unidad (Observer).
        """
        detalle = (
            DetalleGastoComun.objects.select_for_update()
            .select_related("periodo__condominio", "unidad")
            .get(pk=detalle.pk)
        )
        pagado = detalle.pagos.vigentes().aggregate(total=Sum("monto"))["total"] or 0
        saldo = detalle.total - pagado
        if saldo <= 0:
            raise ValidationError("Este cobro ya está pagado completo.")
        if monto > saldo:
            raise ValidationError(f"El pago supera el saldo pendiente (${saldo:,}).".replace(",", "."))

        pago = cls.objects.create(
            detalle=detalle,
            fecha=fecha or timezone.localdate(),
            monto=monto,
            medio=medio,
            observacion=observacion,
            registrado_por=registrado_por,
        )
        if pagado + monto >= detalle.total:
            detalle.estado = DetalleGastoComun.Estado.PAGADO
            detalle.save(update_fields=["estado"])

        residentes = Residente.objects.filter(unidad=detalle.unidad, activo=True).select_related("usuario")
        pago.notificar(
            Evento(
                condominio=detalle.periodo.condominio,
                titulo="Registramos tu pago",
                mensaje=f"Pago de ${monto:,} para {detalle.periodo} ({detalle.unidad}).".replace(",", "."),
                destinatarios=[r.usuario for r in residentes],
                url=reverse("pagos:cobro_detalle", args=[detalle.pk]),
            )
        )
        return pago

    # @spec:pagos-anulacion-de-pagos
    @transaction.atomic
    def anular(self, motivo, anulado_por):
        """
        Anula este pago (Issue #53). No se borra: queda marcado, con motivo, fecha y autor.

        1. Bloquea el cobro igual que registrar(): una anulación y un pago simultáneos
           se ordenan y el saldo nunca se calcula con datos viejos.
        2. Si el cobro estaba PAGADO y sin este pago ya no se cubre el total, vuelve a PENDIENTE.
        3. Queda en la auditoría (#27) en la misma transacción: si algo falla, no queda
           un registro de una anulación que no ocurrió.
        4. Se avisa a los residentes que ven ese cobro (Observer, filtro de residencia C2).
        """
        motivo = (motivo or "").strip()
        if not motivo:
            raise ValidationError("Indica el motivo de la anulación.")
        detalle = (
            DetalleGastoComun.objects.select_for_update()
            .select_related("periodo__condominio", "unidad")
            .get(pk=self.detalle_id)
        )
        # Releer con el cobro ya bloqueado: otra persona pudo anularlo un instante antes.
        self.refresh_from_db(fields=["anulado"])
        if self.anulado:
            raise ValidationError("Este pago ya estaba anulado.")

        self.anulado = True
        self.motivo_anulacion = motivo
        self.anulado_en = timezone.now()
        self.anulado_por = anulado_por
        self.save(update_fields=["anulado", "motivo_anulacion", "anulado_en", "anulado_por"])

        pagado = detalle.pagos.vigentes().aggregate(total=Sum("monto"))["total"] or 0
        if detalle.estado == DetalleGastoComun.Estado.PAGADO and pagado < detalle.total:
            detalle.estado = DetalleGastoComun.Estado.PENDIENTE
            detalle.save(update_fields=["estado"])

        condominio = detalle.periodo.condominio
        registrar(
            anulado_por, condominio, Accion.ANULAR, self,
            antes={"anulado": False}, despues={"anulado": True, "motivo_anulacion": motivo},
        )
        self.notificar(
            Evento(
                condominio=condominio,
                titulo="Anulamos un pago",
                mensaje=(
                    f"Se anuló el pago de ${formatear_monto(self.monto)} del {self.fecha:%d-%m-%Y} "
                    f"para {detalle.periodo} ({detalle.unidad}). Motivo: {motivo}"
                ),
                destinatarios=_residentes_que_ven(detalle),
                url=reverse("pagos:cobro_detalle", args=[detalle.pk]),
            )
        )


def _residentes_que_ven(detalle):
    """
    Usuarios residentes activos de la unidad que pueden ver este cobro (contrato C2, #46).
    Quien llegó después del período no tiene el cobro en "Mi cuenta": avisarle le daría
    un enlace que responde 404 y le hablaría de una deuda que no es suya.
    """
    cobro = DetalleGastoComun.objects.filter(pk=detalle.pk)
    residentes = Residente.objects.filter(unidad=detalle.unidad, activo=True).select_related("usuario")
    # ponytail: una consulta por residente; una unidad tiene pocos residentes.
    return [r.usuario for r in residentes if cobros_visibles(cobro, r.usuario).exists()]
