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
    4. los ítems de cobro (RQ-02, #117) se suman aparte a cada unidad alcanzada, una
       línea por ítem, y no aportan al fondo de reserva (ver lineas_de_items()).
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.servicios import Accion, registrar
from apps.condominios.models import Condominio, Residente, Unidad
from apps.core.formato import formatear_monto
from apps.notificaciones.observador import Evento

from .fondo import fin_mes, guardar_movimiento, validar_cobertura
from .models import MONTO_MAXIMO, DetalleGastoComun, ItemCobro, LineaCobro, MovimientoFondo, PeriodoGasto
from .prorrateo import ESTRATEGIAS, PorAlicuota


@dataclass
class FilaEmision:
    """Lo que paga una unidad en el período."""

    unidad: Unidad
    monto: int          # parte de los egresos
    fondo: int          # parte del fondo de reserva
    lineas: list = field(default_factory=list)  # [(ItemCobro, monto)] de los ítems que la alcanzan

    @property
    def items(self):
        """Suma de los ítems de cobro de la unidad."""
        return sum(monto for _, monto in self.lineas)

    @property
    def total(self):
        return self.monto + self.fondo + self.items


@dataclass
class Emision:
    """Resultado del cálculo: totales, una fila por unidad y los errores que impiden emitir."""

    periodo: PeriodoGasto
    total_egresos: int = 0
    total_fondo: int = 0
    total_items: int = 0
    filas: list = field(default_factory=list)
    errores: list = field(default_factory=list)

    @property
    def puede_emitir(self):
        return not self.errores

    @property
    def total_a_cobrar(self):
        return self.total_egresos + self.total_fondo + self.total_items


def unidades_alcanzadas(item, unidades):
    """Las unidades que paga el ítem: todas, o solo las elegidas (en el orden de `unidades`)."""
    if item.alcance == ItemCobro.Alcance.TODAS:
        return unidades
    elegidas = {u.pk for u in item.unidades.all()}
    return [u for u in unidades if u.pk in elegidas]


def montos_del_item(item, unidades):
    """
    Cuánto paga cada unidad alcanzada por el ítem: {unidad: monto}.

      - POR_UNIDAD: cada una paga item.monto (sin redondeo).
      - PRORRATEO:  item.monto se reparte por alícuota SOLO entre las alcanzadas, con el
                    método del resto mayor (prorrateo.repartir): la suma es exactamente
                    item.monto. Siempre por alícuota, aunque el período reparta los egresos
                    en partes iguales (design.md, decisión 3).
    """
    alcanzadas = unidades_alcanzadas(item, unidades)
    if item.modo == ItemCobro.Modo.POR_UNIDAD:
        return {u: item.monto for u in alcanzadas}
    return PorAlicuota().calcular(item.monto, alcanzadas)


def lineas_de_items(periodo, unidades):
    """
    Reparte los ítems del período: devuelve ({unidad: [(item, monto)]}, errores).
    Cada ítem se reparte por separado, así cada línea cuadra con su ítem.
    """
    lineas = {u: [] for u in unidades}
    errores = []
    for item in periodo.items_cobro.prefetch_related("unidades"):
        montos = montos_del_item(item, unidades)
        # Sin unidades alcanzadas, o a prorratear entre unidades de alícuota 0 (repartir da todo 0):
        # el ítem no se cobraría a nadie. Se rechaza en vez de perderlo en silencio.
        if sum(montos.values()) == 0:
            errores.append(f"El ítem «{item.nombre}» no tiene unidades que lo paguen: revisa su alcance o las alícuotas.")
            continue
        for unidad, monto in montos.items():
            if monto > 0:
                lineas[unidad].append((item, monto))
    return lineas, errores


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
    lineas, errores_items = lineas_de_items(periodo, unidades)
    emision.errores += errores_items
    emision.filas = [FilaEmision(unidad=u, monto=montos[u], fondo=fondos[u], lineas=lineas[u]) for u in unidades]
    emision.total_items = sum(fila.items for fila in emision.filas)
    # Un cobro sobre el máximo desbordaría la columna y casi seguro es un error de tipeo.
    emision.errores += [
        f"El cobro de {fila.unidad} supera ${formatear_monto(MONTO_MAXIMO)}: revisa los ítems de cobro."
        for fila in emision.filas if fila.total > MONTO_MAXIMO
    ]
    return emision


@transaction.atomic
def emitir_periodo(periodo, *, usuario=None):
    """
    Emite el período: crea un DetalleGastoComun por unidad, cambia el período a
    EMITIDO y avisa a los residentes (patrón Observer).

    Lanza ValidationError si no se puede emitir (ver calcular_emision).
    """
    # Siempre condominio antes del período: coordina apertura, manuales y doble emisión.
    condominio = Condominio.objects.select_for_update().get(pk=periodo.condominio_id)
    periodo = PeriodoGasto.objects.select_for_update().get(pk=periodo.pk, condominio=condominio)
    validar_cobertura(condominio, fin_mes(periodo))
    emision = calcular_emision(periodo)
    if not emision.puede_emitir:
        raise ValidationError(emision.errores)

    DetalleGastoComun.objects.bulk_create(
        [
            DetalleGastoComun(periodo=periodo, unidad=fila.unidad, monto=fila.monto, monto_fondo_reserva=fila.fondo,
                              monto_items=fila.items)
            for fila in emision.filas
        ]
    )
    # bulk_create no devuelve los id en MySQL: se leen para colgar las líneas de cada cobro.
    detalles = {d.unidad_id: d for d in periodo.detalles.all()}
    LineaCobro.objects.bulk_create(
        [
            LineaCobro(detalle=detalles[fila.unidad.pk], item=item, nombre=item.nombre, monto=monto)
            for fila in emision.filas
            for item, monto in fila.lineas
        ]
    )
    aporte = int(periodo.detalles.aggregate(total=Sum("monto_fondo_reserva"))["total"] or 0)
    guardar_movimiento(MovimientoFondo(
        condominio=condominio, tipo=MovimientoFondo.Tipo.INGRESO, monto=aporte,
        fecha=fin_mes(periodo), descripcion=f"Aporte de {periodo}", periodo=periodo, creado_por=usuario,
    ), usuario)
    periodo.estado = PeriodoGasto.Estado.EMITIDO
    periodo.fecha_emision = timezone.now()
    periodo.save(update_fields=["estado", "fecha_emision"])

    registrar(usuario, condominio, Accion.MODIFICAR, periodo,
              antes={"estado": PeriodoGasto.Estado.ABIERTO},
              despues={"estado": periodo.estado, "fecha_emision": periodo.fecha_emision, "aporte_fondo": aporte})

    residentes = Residente.objects.filter(activo=True, unidad__edificio__condominio=periodo.condominio)
    periodo.notificar(
        Evento(
            condominio=periodo.condominio,
            titulo="Gastos comunes emitidos",
            mensaje=f"Ya están disponibles los gastos comunes de {periodo}.",
            destinatarios=[r.usuario for r in residentes.select_related("usuario")],
            # Lleva al estado de cuenta del residente (Issue #3).
            url=reverse("pagos:estado_cuenta"),
        )
    )
    return emision


# --------------------------------------------------------------------------
# Ítems de cobro (RQ-02, #117)
# --------------------------------------------------------------------------
def _bloquear_periodo_abierto(periodo):
    """
    Bloquea condominio y período en el MISMO orden que emitir_periodo() (así no hay
    interbloqueo) y revisa que el período siga abierto. Si una emisión llegó antes, el
    cambio del ítem espera a que termine y aquí se rechaza: lo emitido no cambia.
    """
    condominio = Condominio.objects.select_for_update().get(pk=periodo.condominio_id)
    periodo = PeriodoGasto.objects.select_for_update().get(pk=periodo.pk, condominio=condominio)
    if not periodo.esta_abierto:
        raise ValidationError(f"El período {periodo} ya fue emitido: sus ítems de cobro no se pueden modificar.")
    return condominio, periodo


def datos_item(item):
    """Lo que se guarda del ítem en la auditoría (#27)."""
    return {
        "nombre": item.nombre,
        "modo": item.modo,
        "monto": item.monto,
        "alcance": item.alcance,
        "unidades": sorted(str(u) for u in item.unidades.select_related("edificio")),
    }


@transaction.atomic
def guardar_item(item, unidades, *, usuario):
    """
    Crea o actualiza un ítem de cobro y sus unidades (las de alcance ALGUNAS) y lo audita.
    Lanza ValidationError si el período ya se emitió.
    """
    condominio, item.periodo = _bloquear_periodo_abierto(item.periodo)
    nuevo = item.pk is None
    antes = None if nuevo else datos_item(ItemCobro.objects.get(pk=item.pk))
    item.save()
    item.unidades.set(unidades if item.alcance == ItemCobro.Alcance.ALGUNAS else [])
    registrar(usuario, condominio, Accion.CREAR if nuevo else Accion.MODIFICAR, item,
              antes=antes, despues=datos_item(item))
    return item


@transaction.atomic
def eliminar_item(item, *, usuario):
    """Elimina un ítem de un período abierto y deja el registro de auditoría antes de borrarlo."""
    condominio, _ = _bloquear_periodo_abierto(item.periodo)
    registrar(usuario, condominio, Accion.ELIMINAR, item, antes=datos_item(item))
    item.delete()
