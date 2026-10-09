"""
Cálculo y emisión de los gastos comunes de un período (Issue #2, RF02).

Se separa en dos pasos para poder mostrar una VISTA PREVIA antes de emitir:

    calcular_emision(periodo) -> Emision   (no guarda nada: solo calcula y valida)
    emitir_periodo(periodo)   -> Emision   (guarda los cobros, cierra el período y avisa)

Cálculo, para un total de egresos T y un % de fondo de reserva F:
    1. fondo de reserva del condominio = T × F / 100 (redondeado al peso)
    2. cada unidad paga su parte de T y su parte del fondo, según la estrategia de
       prorrateo del período (patrón Strategy, ver prorrateo.py)
    3. el redondeo usa el método del resto mayor: las partes suman EXACTAMENTE
       T y el fondo, sin perder ni agregar pesos.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.condominios.models import Residente, Unidad
from apps.notificaciones.observador import Evento

from .models import DetalleGastoComun, PeriodoGasto
from .prorrateo import ESTRATEGIAS


@dataclass
class FilaEmision:
    """Lo que paga una unidad en el período."""

    unidad: Unidad
    monto: int          # parte de los egresos
    fondo: int          # parte del fondo de reserva

    @property
    def total(self):
        return self.monto + self.fondo


@dataclass
class Emision:
    """Resultado del cálculo: totales, una fila por unidad y los errores que impiden emitir."""

    periodo: PeriodoGasto
    total_egresos: int = 0
    total_fondo: int = 0
    filas: list = field(default_factory=list)
    errores: list = field(default_factory=list)

    @property
    def puede_emitir(self):
        return not self.errores

    @property
    def total_a_cobrar(self):
        return self.total_egresos + self.total_fondo


def calcular_emision(periodo):
    """Calcula cuánto paga cada unidad SIN guardar nada (sirve para la vista previa)."""
    emision = Emision(periodo=periodo)
    condominio = periodo.condominio
    unidades = list(Unidad.objects.filter(edificio__condominio=condominio).select_related("edificio"))
    emision.total_egresos = periodo.total_egresos()

    # Reglas que impiden emitir (criterios de aceptación del Issue #2).
    if not periodo.esta_abierto:
        emision.errores.append("El período ya fue emitido: no se puede emitir dos veces.")
    if emision.total_egresos <= 0:
        emision.errores.append("El período no tiene egresos: registra al menos uno antes de emitir.")
    if not unidades:
        emision.errores.append("El condominio no tiene unidades registradas.")
    if periodo.criterio_prorrateo == PeriodoGasto.Criterio.ALICUOTA:
        suma = condominio.suma_alicuotas()
        if suma != 1:
            emision.errores.append(
                f"Las alícuotas de las unidades suman {suma:.6f} y deben sumar 1 (100 %). Corrígelas en Unidades."
            )
    if emision.errores:
        return emision

    porcentaje = Decimal(periodo.porcentaje_fondo_reserva)
    emision.total_fondo = int(
        (Decimal(emision.total_egresos) * porcentaje / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )

    # Patrón Strategy: la emisión no sabe qué criterio es, solo le pide calcular().
    estrategia = ESTRATEGIAS[periodo.criterio_prorrateo]
    montos = estrategia.calcular(emision.total_egresos, unidades)
    fondos = estrategia.calcular(emision.total_fondo, unidades)
    emision.filas = [FilaEmision(unidad=u, monto=montos[u], fondo=fondos[u]) for u in unidades]
    return emision


@transaction.atomic
def emitir_periodo(periodo):
    """
    Emite el período: crea un DetalleGastoComun por unidad, cambia el período a
    EMITIDO y avisa a los residentes (patrón Observer).

    Lanza ValidationError si no se puede emitir (ver calcular_emision).
    """
    # select_for_update() bloquea la fila del período hasta terminar: si dos
    # personas presionan "Emitir" al mismo tiempo, la segunda espera y luego ve
    # el período ya emitido (no se crean cobros duplicados).
    periodo = PeriodoGasto.objects.select_for_update().select_related("condominio").get(pk=periodo.pk)
    emision = calcular_emision(periodo)
    if not emision.puede_emitir:
        raise ValidationError(emision.errores)

    DetalleGastoComun.objects.bulk_create(
        [
            DetalleGastoComun(periodo=periodo, unidad=fila.unidad, monto=fila.monto, monto_fondo_reserva=fila.fondo)
            for fila in emision.filas
        ]
    )
    periodo.estado = PeriodoGasto.Estado.EMITIDO
    periodo.fecha_emision = timezone.now()
    periodo.save(update_fields=["estado", "fecha_emision"])

    residentes = Residente.objects.filter(activo=True, unidad__edificio__condominio=periodo.condominio)
    periodo.notificar(
        Evento(
            condominio=periodo.condominio,
            titulo="Gastos comunes emitidos",
            mensaje=f"Ya están disponibles los gastos comunes de {periodo}.",
            destinatarios=[r.usuario for r in residentes.select_related("usuario")],
            # El estado de cuenta del residente llega con el Issue #3; mientras, el panel de inicio.
            url=reverse("core:inicio"),
        )
    )
    return emision
