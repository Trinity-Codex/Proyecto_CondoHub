"""
Reporte de gastos comunes y morosidad (Issue #5, RF11).

La Ley 21.442 obliga al administrador a rendir cuentas al comité cada mes:
cuánto se cobró, cuánto se recaudó y quién debe. Este módulo arma ese reporte
para UN período emitido (opcionalmente, de un solo edificio).

Definiciones que usa el reporte:
  - Total emitido:    lo que se cobró a las unidades (gastos + fondo de reserva).
  - Total recaudado:  lo que ya se pagó de esos cobros.
  - % de recaudación: recaudado × 100 / emitido.
  - Saldo:            lo que falta pagar de un cobro (total - pagado).
  - Deuda anterior:   saldos impagos de períodos ANTERIORES al del reporte.
  - Unidad MOROSA:    tiene deuda anterior. Deber solo el mes del reporte no es
                      morosidad: el residente todavía puede pagarlo.

Uso (ver views.py):

    reporte = generar_reporte(periodo, edificio=None)
    reporte.total_emitido, reporte.porcentaje_recaudacion, reporte.filas ...
"""
from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Case, F, IntegerField, Q, Sum, When
from django.db.models.functions import Coalesce

from .models import DetalleGastoComun, PeriodoGasto


def anotar_pagado(cobros):
    """
    Agrega a cada cobro (DetalleGastoComun) dos columnas calculadas por la base de datos:
      - total_cobro: gastos + fondo de reserva
      - pagado:      cuánto se ha pagado de ese cobro

    Es el ÚNICO lugar del reporte donde se decide cuánto se pagó. Sigue la misma
    regla que el estado de cuenta (apps/pagos/consultas.py, Issue #4), para que
    el reporte, la cobranza y "Mi cuenta" muestren siempre los mismos números:
      - cobro PAGADO -> se pagó el total;
      - si no        -> la suma de sus pagos (Pago, related_name="pagos"), que
                        cuenta también los pagos PARCIALES.

    Coalesce(..., 0): un cobro sin pagos da SUM = NULL en SQL; Coalesce lo cambia por 0.
    """
    total = F("monto") + F("monto_fondo_reserva")
    pagado = Case(
        When(estado=DetalleGastoComun.Estado.PAGADO, then=total),
        default=Coalesce(Sum("pagos__monto"), 0),
        output_field=IntegerField(),
    )
    # Ojo: la anotación no puede llamarse "total" porque el modelo ya tiene una
    # propiedad con ese nombre (y Django no puede escribir sobre una propiedad).
    return cobros.annotate(total_cobro=total, pagado=pagado)


@dataclass
class FilaReporte:
    """Una unidad en el reporte: su cobro del período y lo que arrastra de antes."""

    cobro: DetalleGastoComun   # anotado con total_cobro y pagado
    deuda_anterior: int = 0

    @property
    def unidad(self):
        return self.cobro.unidad

    @property
    def total(self):
        return self.cobro.total_cobro

    @property
    def pagado(self):
        return self.cobro.pagado

    @property
    def saldo(self):
        return self.total - self.pagado

    @property
    def deuda_total(self):
        """Lo que la unidad debe en total: el saldo de este período + la deuda anterior."""
        return self.saldo + self.deuda_anterior

    @property
    def es_morosa(self):
        return self.deuda_anterior > 0

    @property
    def situacion(self):
        """Texto corto para la tabla y el CSV."""
        if self.es_morosa:
            return "Morosa"
        if self.saldo > 0:
            return "Pendiente"
        return "Al día"


@dataclass
class ReporteMorosidad:
    """Resultado del reporte: los totales se calculan a partir de las filas, así siempre cuadran."""

    periodo: PeriodoGasto
    edificio: object = None    # Edificio o None (= todos)
    filas: list = field(default_factory=list)

    @property
    def total_emitido(self):
        return sum(f.total for f in self.filas)

    @property
    def total_recaudado(self):
        return sum(f.pagado for f in self.filas)

    @property
    def saldo_periodo(self):
        return self.total_emitido - self.total_recaudado

    @property
    def deuda_anterior(self):
        return sum(f.deuda_anterior for f in self.filas)

    @property
    def deuda_total(self):
        return self.saldo_periodo + self.deuda_anterior

    @property
    def porcentaje_recaudacion(self):
        """Con un decimal, ej. 87.5. Si no se emitió nada, 0."""
        if not self.total_emitido:
            return 0
        return round(self.total_recaudado * 100 / self.total_emitido, 1)

    @property
    def unidades_con_deuda(self):
        return [f for f in self.filas if f.deuda_total > 0]

    @property
    def unidades_morosas(self):
        return [f for f in self.filas if f.es_morosa]


def generar_reporte(periodo, edificio=None):
    """Arma el reporte de un período EMITIDO, de todo el condominio o de un edificio."""
    # 1) Los cobros del período, uno por unidad, ordenados como en el resto del sitio.
    cobros = anotar_pagado(periodo.detalles.select_related("unidad__edificio")).order_by(
        "unidad__edificio__nombre", "unidad__piso", "unidad__numero"
    )

    # 2) Los cobros de períodos emitidos ANTERIORES (mismo condominio) para la deuda anterior.
    #    "Anterior" = año menor, o el mismo año con un mes menor.
    anteriores = anotar_pagado(
        DetalleGastoComun.objects.filter(
            periodo__condominio=periodo.condominio, periodo__estado=PeriodoGasto.Estado.EMITIDO
        ).filter(Q(periodo__anio__lt=periodo.anio) | Q(periodo__anio=periodo.anio, periodo__mes__lt=periodo.mes))
    )

    if edificio is not None:
        cobros = cobros.filter(unidad__edificio=edificio)
        anteriores = anteriores.filter(unidad__edificio=edificio)

    # Saldo impago acumulado por unidad. values() trae solo esas columnas (más liviano que el objeto completo).
    deuda_anterior = defaultdict(int)
    for fila in anteriores.values("unidad_id", "total_cobro", "pagado"):
        deuda_anterior[fila["unidad_id"]] += fila["total_cobro"] - fila["pagado"]

    filas = [FilaReporte(cobro=c, deuda_anterior=deuda_anterior[c.unidad_id]) for c in cobros]
    return ReporteMorosidad(periodo=periodo, edificio=edificio, filas=filas)
