"""
Filtros de formulario del contrato C6 (Issue #75).

Uso en una plantilla:

    {% load formularios %}
    {{ campo|control }}          {# widget con la clase de Bootstrap y los atributos ARIA #}
    {% if campo|es_casilla %}    {# casilla simple: va con form-check #}

Lo normal es no llamarlos a mano: `{% include "_campo.html" with campo=form.x %}` los usa.
"""
from django import forms, template

register = template.Library()

# Clases de Bootstrap que pone BootstrapMixin; el filtro las reemplaza por la correcta.
_CLASES_BASE = {"form-control", "form-select", "form-check-input"}


def _clase_control(widget):
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return "form-check-input"
    if isinstance(widget, forms.Select):
        return "form-select"
    return "form-control"


@register.filter
def control(campo):
    """
    Dibuja el widget con la clase de Bootstrap que le corresponde. Es idempotente: no duplica
    las clases que ya puso BootstrapMixin. Con error agrega `is-invalid`, `aria-invalid="true"`
    y `aria-describedby` con los ids de la ayuda y del error. Sin error no agrega `aria-invalid`.
    """
    widget = campo.field.widget
    clases = [c for c in widget.attrs.get("class", "").split() if c not in _CLASES_BASE]
    clases.append(_clase_control(widget))
    atributos = {}
    descripciones = []
    if campo.help_text:
        descripciones.append(f"{campo.auto_id}_helptext")
    if campo.errors:
        clases.append("is-invalid")
        atributos["aria-invalid"] = "true"
        descripciones.append(f"{campo.auto_id}_error")
    # Los grupos de opciones (radio, casillas múltiples) llevan aria-describedby en su fieldset.
    if descripciones and not widget.use_fieldset:
        atributos["aria-describedby"] = " ".join(descripciones)
    atributos["class"] = " ".join(clases)
    return campo.as_widget(attrs=atributos)


@register.filter
def es_casilla(campo):
    """True para una casilla simple (no para un grupo de casillas)."""
    return isinstance(campo.field.widget, forms.CheckboxInput)
