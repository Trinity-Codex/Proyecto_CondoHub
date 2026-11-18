"""Consultas del estado de cuenta (Issues #3 y #4). Las vistas las comparten para dar los mismos números."""
from django.db.models import Sum

from apps.condominios.residencias import cobros_visibles
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto
from apps.gastos.reportes import generar_reporte


def cobros_del_residente(usuario, condominio):
    """
    Cobros EMITIDOS de las unidades donde el usuario vive (residente activo),
    del más reciente al más antiguo. Es la única fuente de "qué cobros puede ver
    un residente": la lista y el detalle la usan, así un cobro ajeno da 404.
    """
    cobros = (
        DetalleGastoComun.objects.filter(
            periodo__condominio=condominio,
            periodo__estado=PeriodoGasto.Estado.EMITIDO,  # lo no emitido aún no se cobra
            # Las dos condiciones del residente van en el MISMO filter(): así deben
            # cumplirse en la misma fila de Residente (este usuario Y activo). En dos
            # filter() separados podría coincidir un residente activo cualquiera de la unidad.
            unidad__residentes__usuario=usuario,
            unidad__residentes__activo=True,
        )
        .select_related("periodo", "unidad__edificio")
        .prefetch_related("pagos")  # una consulta para todos los pagos (evita una por cobro)
        .distinct()  # si la unidad tiene varios residentes, el JOIN repetiría el cobro
        .order_by("-periodo__anio", "-periodo__mes", "unidad__numero")
    )
    return cobros_visibles(cobros, usuario)  # solo los meses de su residencia (Issue #46)


def pagado_del_cobro(cobro):
    """
    Suma de los pagos VIGENTES del cobro (contrato C4, #53): un pago anulado no rebaja la deuda.
    Es la misma regla que Pago.objects.vigentes(), pero aplicada sobre cobro.pagos.all() para
    aprovechar el prefetch_related("pagos") de quien llama (cobranza, recordatorios, descarga
    de datos); cobro.pagos.vigentes() haría una consulta por cobro.
    Saldo, total adeudado, Mi cuenta, el panel y la cobranza calculan todos a partir de aquí.
    """
    return sum(p.monto for p in cobro.pagos.all() if not p.anulado)


def saldo_del_cobro(cobro):
    """Lo que aún falta pagar del cobro (0 si ya está pagado)."""
    if cobro.estado == DetalleGastoComun.Estado.PAGADO:
        return 0
    return max(cobro.total - pagado_del_cobro(cobro), 0)


def con_saldos(cobros):
    """Devuelve la lista de cobros con .pagado y .saldo ya calculados (para las plantillas)."""
    cobros = list(cobros)
    for c in cobros:
        c.pagado = pagado_del_cobro(c)
        c.saldo = saldo_del_cobro(c)
    return cobros


def total_adeudado(cobros):
    """
    Total que se debe: el SALDO de los cobros pendientes o morosos. Con pagos
    parciales, un cobro de $42.000 con $10.000 abonados suma $32.000.
    """
    deuda = (DetalleGastoComun.Estado.PENDIENTE, DetalleGastoComun.Estado.MOROSO)
    return sum(saldo_del_cobro(c) for c in cobros if c.estado in deuda)


def reporte_del_ultimo_periodo(condominio):
    """
    Reporte de recaudación y morosidad del último período EMITIDO del condominio (el mismo que el reporte
    muestra por defecto), o None si aún no se emite ninguno. Lo usan el inicio y la página Cobranza (#57, #79).
    """
    ultimo = PeriodoGasto.objects.filter(condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO).first()
    return generar_reporte(ultimo) if ultimo else None


# Las remuneraciones se muestran con un nombre propio y nunca por persona ni por cargo (Issue #115).
_ETIQUETA_REMUNERACIONES = "Remuneraciones del personal"


# @spec:pagos-estado-de-cuenta-del-residente
def egresos_para_residente(periodo):
    """
    Egresos del período tal como puede verlos un RESIDENTE (Issue #115, RQ-09): agrupados por
    categoría, con su subtotal. Devuelve una lista de dicts {"categoria": texto legible,
    "subtotal": pesos}, de mayor a menor subtotal (y por nombre si empatan, para un orden estable).

    Por qué existe: la descripción libre de un egreso puede nombrar a un trabajador o a un tercero
    y los sueldos individuales son datos personales. Aquí no sale descripción, proveedor ni fecha
    de boleta; las remuneraciones salen como UNA sola línea («Remuneraciones del personal»).
    La suma de los subtotales es exactamente periodo.total_egresos().

    Es la ÚNICA fuente de egresos para el residente. El aviso de cobro (#6) y la rendición de
    cuentas (#55) deben reutilizarla en vez de recorrer periodo.egresos. El detalle línea a línea
    sigue solo para administrador y comité en gastos:periodo_detalle.
    """
    nombres = dict(Egreso.Categoria.choices)
    nombres[Egreso.Categoria.REMUNERACIONES] = _ETIQUETA_REMUNERACIONES
    resumen = periodo.egresos.order_by().values("categoria").annotate(subtotal=Sum("monto"))
    lineas = [{"categoria": nombres[fila["categoria"]], "subtotal": fila["subtotal"]} for fila in resumen]
    return sorted(lineas, key=lambda linea: (-linea["subtotal"], linea["categoria"]))
