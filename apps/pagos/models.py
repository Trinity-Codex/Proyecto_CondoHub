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

from apps.condominios.models import Residente
from apps.gastos.models import DetalleGastoComun
from apps.notificaciones.observador import Evento, Sujeto


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

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self):
        return f"Pago ${self.monto} de {self.detalle}"

    @property
    def condominio(self):
        return self.detalle.periodo.condominio

    @classmethod
    @transaction.atomic
    def registrar(cls, detalle, monto, fecha=None, medio=Medio.TRANSFERENCIA, observacion="", registrado_por=None):
        """
        Registra un pago sobre un cobro. Todo ocurre en UNA transacción:

        1. select_for_update() bloquea la fila del cobro: si dos personas registran
           un pago al mismo tiempo, la segunda espera y ve el saldo ya actualizado
           (así nunca se paga de más por una carrera entre dos clics).
        2. No se acepta más que el saldo pendiente.
        3. Si con este pago se alcanza el total, el cobro pasa a PAGADO.
        4. Se avisa a los residentes de la unidad (Observer).
        """
        detalle = (
            DetalleGastoComun.objects.select_for_update()
            .select_related("periodo__condominio", "unidad")
            .get(pk=detalle.pk)
        )
        pagado = detalle.pagos.aggregate(total=Sum("monto"))["total"] or 0
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
