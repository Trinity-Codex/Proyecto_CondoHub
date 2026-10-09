"""
Consultas compartidas del estado de cuenta.

La regla de oro: un residente SOLO ve los cobros de las unidades donde vive
(residente activo) y solo de períodos ya EMITIDOS en el condominio activo.
"""
from apps.gastos.models import DetalleGastoComun, PeriodoGasto


def cobros_del_residente(usuario, condominio):
    """Cobros emitidos de todas las unidades del usuario en el condominio."""
    return (
        DetalleGastoComun.objects.filter(
            periodo__condominio=condominio,
            periodo__estado=PeriodoGasto.Estado.EMITIDO,  # lo no emitido aún no se cobra
            unidad__residentes__usuario=usuario,
            unidad__residentes__activo=True,  # en el mismo filter(): es la MISMA fila de residente
        )
        .select_related("periodo", "unidad__edificio")
        .distinct()  # si una unidad tiene varios residentes, evita filas repetidas
        .order_by("-periodo__anio", "-periodo__mes", "unidad__numero")
    )


def total_adeudado(cobros):
    """Suma de lo que se debe: cobros pendientes y morosos. Los pagados no cuentan."""
    deuda = (DetalleGastoComun.Estado.PENDIENTE, DetalleGastoComun.Estado.MOROSO)
    return sum(c.total for c in cobros if c.estado in deuda)