"""
Campos de formulario propios de CondoHub (Issues #76 y #77).

Uso: `monto = MontoField(label="Monto", min_value=1)` en un Form, o `field_classes = {"monto": MontoField}`
en el Meta de un ModelForm (se conservan los validadores del modelo). `_campo.html` pone el prefijo «$» solo.
Para RUT: `rut = RutField(label="RUT")` o `field_classes = {"rut": RutField}`; `cleaned_data` sale normalizado.
"""
from django import forms

from apps.cuentas.validadores import validar_rut

from .formato import formatear_monto, formatear_rut, normalizar_monto, normalizar_rut

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


class RutInput(forms.TextInput):
    """
    Texto para RUT: `data-rut` (lo activa el JS), placeholder ficticio válido y valor mostrado con puntos.
    `aviso_vivo` hace que `_campo.html` agregue la región aria-live donde el JS escribe «RUT válido.».
    """

    aviso_vivo = True

    def __init__(self, attrs=None):
        por_defecto = {
            "data-rut": "", "autocomplete": "off", "spellcheck": "false", "autocapitalize": "characters",
            "placeholder": "12.345.678-5",
        }
        super().__init__(attrs={**por_defecto, **(attrs or {})})

    def format_value(self, value):
        if value in (None, ""):
            return None
        # Un valor inválido se devuelve tal cual: la persona ve lo que escribió junto al error.
        return formatear_rut(str(value))


class RutField(forms.CharField):
    """RUT chileno: acepta puntos y «k» minúscula, valida igual que antes y entrega `12345678-5`."""

    widget = RutInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 12)
        kwargs.setdefault("validators", [validar_rut])
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        # Sin maxlength: el navegador descartaría en silencio el carácter 13 (o una inserción en un RUT con puntos).
        # El largo máximo se sigue validando en el servidor.
        atributos = super().widget_attrs(widget)
        atributos.pop("maxlength", None)
        return atributos

    def to_python(self, value):
        valor = super().to_python(value)
        return normalizar_rut(valor) if valor else valor
