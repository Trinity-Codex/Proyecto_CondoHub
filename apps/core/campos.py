"""
Campos de formulario propios de CondoHub (Issue #76). #77 agregará aquí `RutField`.

Uso: `monto = MontoField(label="Monto", min_value=1)` en un Form, o `field_classes = {"monto": MontoField}`
en el Meta de un ModelForm (se conservan los validadores del modelo). `_campo.html` pone el prefijo «$» solo.
"""
from django import forms

from .formato import formatear_monto, normalizar_monto

# Regla de negocio y mensaje que debe ser igual en todos los campos de dinero.
MENSAJE_MONTO_INVALIDO = "Escriba el monto en pesos, sin decimales. Ej.: 1.250.000."


class MontoInput(forms.TextInput):
    """Texto para pesos: teclado numérico, `data-monto` (lo activa el JS) y prefijo «$» en `_campo.html`."""

    prefijo = "$"

    def __init__(self, attrs=None):
        por_defecto = {"inputmode": "numeric", "autocomplete": "off", "data-monto": "", "placeholder": "Ej.: 85.000"}
        super().__init__(attrs={**por_defecto, **(attrs or {})})

    def format_value(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, int):
            return formatear_monto(value)
        digitos = normalizar_monto(value)
        # Un texto inválido se devuelve tal cual: la persona ve lo que escribió junto al error.
        return formatear_monto(int(digitos)) if digitos is not None else str(value)


class MontoField(forms.IntegerField):
    """Entero en pesos que acepta puntos de miles y «$». Hereda min_value y max_value de IntegerField."""

    widget = MontoInput

    def to_python(self, value):
        if value in self.empty_values:
            return None
        digitos = normalizar_monto(value)
        if digitos is None:
            raise forms.ValidationError(MENSAJE_MONTO_INVALIDO, code="invalid")
        return super().to_python(digitos)
