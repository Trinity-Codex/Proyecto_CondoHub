"""
Utilidades para formularios con el estilo de Bootstrap.

Bootstrap necesita que cada <input> tenga la clase "form-control" (o
"form-select" en las listas, "form-check-input" en las casillas). En vez de
escribirla campo por campo, los formularios heredan de FormularioBootstrap y
la clase se agrega sola. Así un formulario nuevo queda con buen aspecto sin
código extra (ver docs/GUIA_NUEVA_FEATURE.md).
"""
from django import forms


class BootstrapMixin:
    """Agrega las clases CSS de Bootstrap a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                clase = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()


class FormularioBootstrap(BootstrapMixin, forms.Form):
    """Formulario común con estilo Bootstrap."""


class ModeloFormularioBootstrap(BootstrapMixin, forms.ModelForm):
    """Formulario basado en un modelo (ModelForm) con estilo Bootstrap."""


# Widgets HTML5 para que el navegador muestre un calendario y un selector de hora.
class CampoFecha(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class CampoHora(forms.TimeInput):
    input_type = "time"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%H:%M")
