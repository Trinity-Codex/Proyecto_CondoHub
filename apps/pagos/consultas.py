"""Consultas del estado de cuenta (Issues #3 y #4). Las vistas las comparten para dar los mismos números."""
from apps.gastos.models import DetalleGastoComun, PeriodoGasto


def cobros_del_residente(usuario, condominio):
    """
    Cobros EMITIDOS de las unidades donde el usuario vive (residente activo),
    del más reciente al más antiguo. Es la única fuente de "qué cobros puede ver
    un residente": la lista y el detalle la usan, así un cobro ajeno da 404.
    """
    return (
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


def pagado_del_cobro(cobro):
    """Suma de los pagos registrados contra el cobro."""
    return sum(p.monto for p in cobro.pagos.all())


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
