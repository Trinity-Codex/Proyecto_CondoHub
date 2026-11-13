"""
Filtros de plantilla propios de CondoHub.

Uso en cualquier plantilla:
    {% load condohub %}
    {{ egreso.monto|pesos }}      ->  $1.234.567
    {{ usuario.rut|rut }}         ->  12.345.678-5
"""
from django import template

from apps.core.formato import formatear_monto, formatear_rut

register = template.Library()


@register.filter
def pesos(valor):
    """Formatea un monto en pesos chilenos: punto como separador de miles y sin decimales."""
    if valor in (None, ""):
        return "$0"
    try:
        numero = round(float(valor))
    except (TypeError, ValueError):
        return valor  # si no es un número, se muestra tal cual
    signo = "-" if numero < 0 else ""
    return f"{signo}${formatear_monto(abs(numero))}"


@register.filter
def rut(valor):
    """RUT con puntos para mostrar. None y "" dan "" (se puede encadenar |default:"—"); lo que no es un RUT queda igual."""
    if valor in (None, ""):
        return ""
    return formatear_rut(valor)
