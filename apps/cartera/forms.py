"""Formulario de la cartera: el mes que se consulta (GET, Issue #54)."""
from django import forms

from apps.core.formularios import FormularioBootstrap
from apps.gastos.models import MESES


def nombre_mes(anio, mes):
    """«Octubre 2026», como se muestra un período en el resto del sitio."""
    return f"{MESES[mes - 1].capitalize()} {anio}"


def clave_mes(anio, mes):
    """El valor de `?mes=`: «2026-10»."""
    return f"{anio}-{mes:02d}"


def leer_mes(texto, disponibles):
    """El (año, mes) de un `?mes=AAAA-MM` si está entre los `disponibles`; si no, None (se ignora)."""
    for anio, mes in disponibles:
        if texto == clave_mes(anio, mes):
            return anio, mes
    return None


class FiltroMesForm(FormularioBootstrap):
    """Selector del mes: solo ofrece los meses con algún período emitido en la cartera."""

    mes = forms.ChoiceField(label="Mes", choices=[])

    def __init__(self, *args, disponibles, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mes"].choices = [(clave_mes(a, m), nombre_mes(a, m)) for a, m in disponibles]
