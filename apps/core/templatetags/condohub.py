"""
Filtros de plantilla propios de CondoHub.

Uso en cualquier plantilla:
    {% load condohub %}
    {{ egreso.monto|pesos }}      ->  $1.234.567
"""
from django import template

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
    # f"{1234567:,}" -> "1,234,567"; en Chile el separador de miles es el punto.
    return f"{signo}${abs(numero):,}".replace(",", ".")
