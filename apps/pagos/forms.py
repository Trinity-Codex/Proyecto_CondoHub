"""Formulario para registrar un pago (Issue #4, RF04)."""
from django import forms
from django.utils import timezone

from apps.core.formularios import CampoFecha, FormularioBootstrap

from .consultas import saldo_del_cobro
from .models import Pago


class PagoForm(FormularioBootstrap):
    """
    Datos del pago. Recibe el cobro (detalle) para validar contra su saldo y
    mostrar el error en el campo "monto" antes de intentar guardar. La validación
    definitiva (con el cobro bloqueado) está en Pago.registrar().
    """

    monto = forms.IntegerField(label="Monto pagado ($)", min_value=1)
    fecha = forms.DateField(label="Fecha del pago", widget=CampoFecha(), initial=timezone.localdate)
    medio = forms.ChoiceField(label="Medio de pago", choices=Pago.Medio.choices)
    observacion = forms.CharField(label="Observación", max_length=200, required=False)

    def __init__(self, *args, detalle, **kwargs):
        super().__init__(*args, **kwargs)
        self.detalle = detalle
        self.saldo = saldo_del_cobro(detalle)
        if not self.is_bound:
            # Por defecto sugiere pagar el saldo completo (el caso más común).
            self.fields["monto"].initial = self.saldo

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto > self.saldo:
            raise forms.ValidationError(f"No puede superar el saldo pendiente (${self.saldo:,}).".replace(",", "."))
        return monto

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha del pago no puede ser futura.")
        return fecha
