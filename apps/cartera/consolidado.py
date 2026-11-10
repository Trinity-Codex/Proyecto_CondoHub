"""
Cifras de la cartera: una fila por condominio y un mes (Issue #54, RF18).

No hay SQL propio: cada fila sale de `generar_reporte` (apps/gastos/reportes.py), el mismo cálculo del
reporte de recaudación de ese condominio. Por eso las cifras cuadran por construcción y, cuando se corrija
`anotar_pagado` (C4, #53), la cartera cambia junto con el reporte.

    meses = meses_disponibles(condominios)           # [(2026, 10), (2026, 9), ...], el más reciente primero
    cartera = armar_cartera(condominios, meses[0])
    cartera.filas, cartera.total_emitido, cartera.porcentaje_recaudacion ...
"""
from dataclasses import dataclass, field

from apps.gastos.models import PeriodoGasto
from apps.gastos.reportes import ReporteMorosidad, generar_reporte


@dataclass
class FilaCartera:
    """Un condominio en la cartera. `reporte` es None si no tiene emitido el período del mes."""

    condominio: object
    reporte: ReporteMorosidad | None = None

    @property
    def tiene_periodo(self):
        return self.reporte is not None

    @property
    def periodo(self):
        return self.reporte.periodo if self.reporte else None

    @property
    def emitido(self):
        return self.reporte.total_emitido if self.reporte else 0

    @property
    def recaudado(self):
        return self.reporte.total_recaudado if self.reporte else 0

    @property
    def porcentaje_recaudacion(self):
        return self.reporte.porcentaje_recaudacion if self.reporte else 0

    @property
    def deuda_anterior(self):
        return self.reporte.deuda_anterior if self.reporte else 0

    @property
    def unidades_morosas(self):
        """Cantidad de unidades con deuda de períodos anteriores (no sus nombres: RNF08)."""
        return len(self.reporte.unidades_morosas) if self.reporte else 0


@dataclass
class Cartera:
    """Resultado para un mes. Los totales suman las filas CON período; el % se calcula sobre los totales."""

    anio: int
    mes: int
    filas: list = field(default_factory=list)

    @property
    def total_emitido(self):
        return sum(fila.emitido for fila in self.filas)

    @property
    def total_recaudado(self):
        return sum(fila.recaudado for fila in self.filas)

    @property
    def deuda_anterior(self):
        return sum(fila.deuda_anterior for fila in self.filas)

    @property
    def unidades_morosas(self):
        return sum(fila.unidades_morosas for fila in self.filas)

    @property
    def porcentaje_recaudacion(self):
        """Recaudado total × 100 / emitido total, con un decimal, igual que el reporte. Sin emitido, 0,0."""
        if not self.total_emitido:
            return 0.0
        return round(self.total_recaudado * 100 / self.total_emitido, 1)


def _emitidos(condominios):
    return PeriodoGasto.objects.filter(condominio__in=condominios, estado=PeriodoGasto.Estado.EMITIDO)


def meses_disponibles(condominios):
    """Meses (año, mes) con algún período emitido en los condominios dados, del más reciente al más antiguo."""
    return list(_emitidos(condominios).values_list("anio", "mes").distinct().order_by("-anio", "-mes"))


def armar_cartera(condominios, anio, mes):
    """La cartera de `condominios` (en su orden) para el mes dado; una consulta busca los períodos de todos."""
    periodos = {
        periodo.condominio_id: periodo
        for periodo in _emitidos(condominios).filter(anio=anio, mes=mes).select_related("condominio")
    }
    filas = []
    for condominio in condominios:
        periodo = periodos.get(condominio.pk)
        filas.append(FilaCartera(condominio, generar_reporte(periodo) if periodo else None))
    return Cartera(anio=anio, mes=mes, filas=filas)
