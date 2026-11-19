"""
Proyección anual de gastos comunes con IPC y crecimiento (RQ-06, Issue #121). Solo lectura.

La pantalla y el CSV salen de proyectar(), así muestran siempre los mismos números.
Decisiones (todas SUPUESTOS PROVISORIOS mientras el cliente responde la consulta C7) en
openspec/changes/agregar-proyeccion-anual-de-gastos/design.md:

  - Base de cada mes: egresos del período EMITIDO de ese mes del año base. Los períodos
    abiertos no cuentan (sus egresos pueden cambiar) y los ítems de cobro (#117) tampoco:
    son cargos puntuales que no se repiten el año siguiente.
  - Mes sin período emitido: el promedio de los meses reales, marcado como estimado.
  - Fórmula: base × (1 + IPC/100) × (1 + crecimiento/100), redondeada al peso UNA vez.
    Ej.: 100.000 con IPC 10 % y crecimiento 10 % -> 100.000 × 1,1 × 1,1 = 121.000.
  - Fondo de reserva del mes: egresos proyectados × % del fondo vigente, redondeado como en
    la emisión (servicios.calcular_emision).
  - Reparto por unidad con la estrategia de prorrateo vigente (patrón Strategy): repartir()
    usa el resto mayor, así lo de las unidades suma EXACTO el total de cada mes.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

from apps.condominios.models import Unidad

from .models import MESES, PeriodoGasto
from .prorrateo import ESTRATEGIAS


def redondear(valor):
    """Decimal -> pesos enteros, con el mismo redondeo que la emisión (0,5 sube)."""
    return int(Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def porcentaje_texto(valor):
    """Decimal -> texto con coma decimal y sin ceros de más: Decimal("4.50") -> "4,5 %"."""
    return format(Decimal(valor).normalize(), "f").replace(".", ",") + " %"


def reajustar(base, ipc, crecimiento):
    """Monto del año siguiente: base × (1 + IPC/100) × (1 + crecimiento/100), al peso."""
    factor = (1 + Decimal(ipc) / 100) * (1 + Decimal(crecimiento) / 100)
    return redondear(Decimal(base) * factor)


@dataclass
class MesProyectado:
    """Un mes del año proyectado."""

    mes: int
    base: int  # egresos del mes en el año base (real o promedio)
    estimado: bool  # True: el año base no tuvo período emitido ese mes
    egresos: int  # egresos proyectados
    fondo: int  # fondo de reserva proyectado
    por_unidad: list = field(default_factory=list)  # [(egresos, fondo)] en el orden de Proyeccion.unidades

    @property
    def nombre(self):
        return MESES[self.mes - 1].capitalize()

    @property
    def total(self):
        return self.egresos + self.fondo


@dataclass
class Proyeccion:
    anio_base: int
    ipc: Decimal
    crecimiento: Decimal
    criterio: str  # clave de ESTRATEGIAS
    porcentaje_fondo: Decimal
    unidades: list = field(default_factory=list)
    meses: list = field(default_factory=list)  # 12 MesProyectado, o vacía si no hay meses reales
    meses_reales: int = 0
    aviso_alicuotas: str = ""

    @property
    def anio(self):
        """Año proyectado."""
        return self.anio_base + 1

    @property
    def criterio_nombre(self):
        return ESTRATEGIAS[self.criterio].nombre

    @property
    def meses_estimados(self):
        return [m for m in self.meses if m.estimado]

    @property
    def total_base(self):
        return sum(m.base for m in self.meses)

    @property
    def total_egresos(self):
        return sum(m.egresos for m in self.meses)

    @property
    def total_fondo(self):
        return sum(m.fondo for m in self.meses)

    @property
    def total(self):
        return self.total_egresos + self.total_fondo

    @property
    def supuestos(self):
        """Cuadro de supuestos: [(texto, valor)], el mismo en la pantalla y en el CSV."""
        estimados = ", ".join(m.nombre.lower() for m in self.meses_estimados) or "ninguno"
        return [
            ("Año base", str(self.anio_base)),
            ("Año proyectado", str(self.anio)),
            ("IPC anual", porcentaje_texto(self.ipc)),
            ("Crecimiento anual", porcentaje_texto(self.crecimiento)),
            ("Fórmula", "egresos del mes base × (1 + IPC) × (1 + crecimiento), al peso"),
            ("Criterio de prorrateo", self.criterio_nombre),
            ("Fondo de reserva", porcentaje_texto(self.porcentaje_fondo) + " de los egresos"),
            ("Meses reales (períodos emitidos)", str(self.meses_reales)),
            ("Meses estimados con el promedio", estimados),
            ("Ítems de cobro", "fuera de la base (cargos puntuales)"),
        ]

    @property
    def filas_unidades(self):
        """Por unidad: total de cada mes y del año (egresos + fondo)."""
        filas = []
        for i, unidad in enumerate(self.unidades):
            por_mes = [sum(m.por_unidad[i]) for m in self.meses]
            egresos = sum(m.por_unidad[i][0] for m in self.meses)
            fondo = sum(m.por_unidad[i][1] for m in self.meses)
            filas.append({"unidad": unidad, "por_mes": por_mes, "egresos": egresos, "fondo": fondo, "total": egresos + fondo})
        return filas


def bases_del_anio(condominio, anio):
    """{mes: egresos} de los períodos EMITIDOS del año (solo Egreso: sin ítems de cobro)."""
    filas = (
        PeriodoGasto.objects.filter(condominio=condominio, anio=anio, estado=PeriodoGasto.Estado.EMITIDO)
        .annotate(suma=Sum("egresos__monto")).values_list("mes", "suma")
    )
    return {mes: int(suma or 0) for mes, suma in filas}


def criterio_vigente(condominio):
    """(criterio, % del fondo) del período más reciente; sin períodos, los valores por defecto del modelo."""
    ultimo = PeriodoGasto.objects.filter(condominio=condominio).order_by("-anio", "-mes").first()
    if ultimo is None:
        defecto = PeriodoGasto()
        return defecto.criterio_prorrateo, Decimal(defecto.porcentaje_fondo_reserva)
    return ultimo.criterio_prorrateo, Decimal(ultimo.porcentaje_fondo_reserva)


def proyectar(condominio, anio_base, ipc, crecimiento):
    """
    Proyección del año anio_base + 1. Mismos datos y parámetros -> mismo resultado
    (sin azar ni fecha de hoy en el cálculo). Si el año base no tiene meses emitidos,
    la lista de meses queda vacía: no se inventa una proyección.
    """
    criterio, porcentaje = criterio_vigente(condominio)
    unidades = list(
        Unidad.objects.filter(edificio__condominio=condominio).select_related("edificio")
        .order_by("edificio__nombre", "piso", "numero", "pk")
    )
    proyeccion = Proyeccion(anio_base=anio_base, ipc=Decimal(ipc), crecimiento=Decimal(crecimiento),
                            criterio=criterio, porcentaje_fondo=porcentaje, unidades=unidades)
    if criterio == PeriodoGasto.Criterio.ALICUOTA and unidades and condominio.suma_alicuotas() != 1:
        proyeccion.aviso_alicuotas = (
            f"Las alícuotas suman {condominio.suma_alicuotas():.6f} y no 1: la proyección reparte en proporción "
            "a ellas, pero la emisión real lo rechazaría hasta corregirlas."
        )

    reales = bases_del_anio(condominio, anio_base)
    proyeccion.meses_reales = len(reales)
    if not reales:
        return proyeccion
    promedio = redondear(Decimal(sum(reales.values())) / len(reales))
    estrategia = ESTRATEGIAS[criterio]
    for mes in range(1, 13):
        base = reales.get(mes, promedio)
        egresos = reajustar(base, ipc, crecimiento)
        fondo = redondear(Decimal(egresos) * porcentaje / 100)
        montos = estrategia.calcular(egresos, unidades)
        fondos = estrategia.calcular(fondo, unidades)
        proyeccion.meses.append(MesProyectado(
            mes=mes, base=base, estimado=mes not in reales, egresos=egresos, fondo=fondo,
            por_unidad=[(montos[u], fondos[u]) for u in unidades],
        ))
    return proyeccion
