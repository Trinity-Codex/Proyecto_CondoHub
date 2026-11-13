"""
Datos demo de pagos (Issues #4, #5 y #62), sobre los períodos emitidos de apps/gastos/demo.py:
  - hace dos meses: pagaron todos menos A-102 y B-202 (quedan morosas);
  - mes anterior: la mitad pagó, B-201 hizo un abono PARCIAL y el resto debe
    (sirve para el estado de cuenta, la cobranza y el reporte);
  - mes anterior: un pago de A-101 registrado por error y ANULADO (#53), para que la cuenta
    de la unidad, "Mi cuenta" del residente demo, su aviso y la auditoría muestren una anulación.
Cada pago se fecha el último día del mes de su período.
"""
import calendar
from datetime import date

from apps.pagos.models import Pago


def cargar(datos):
    periodos = datos["periodos"]
    _registrar_pagos(datos, periodos["hace_dos_meses"], excepto=["A-102", "B-202"])
    anterior = periodos["anterior"]
    _registrar_pagos(datos, anterior, solo=["A-201", "A-202", "A-301", "B-101", "B-301"])
    _registrar_pagos(datos, anterior, solo=["B-201"], monto=100000)  # abono parcial
    _anular_pago_demo(datos, anterior)


def _anular_pago_demo(datos, periodo):
    """
    A-101 (el residente demo) sigue debiendo el mes anterior: se le registra un pago por error
    y se anula con Pago.anular(), igual que lo haría el administrador. El cobro vuelve a
    PENDIENTE, así la cobranza y el reporte no cambian por tener este pago en la demo.
    """
    cobro = periodo.detalles.get(unidad=datos["unidades"]["A-101"])
    admin = datos["usuarios"]["administrador"]
    fecha = date(periodo.anio, periodo.mes, calendar.monthrange(periodo.anio, periodo.mes)[1])
    pago = Pago.registrar(cobro, monto=cobro.total, fecha=fecha, registrado_por=admin)
    pago.anular("La transferencia era de otra unidad (dato ficticio de la demo).", anulado_por=admin)


def _registrar_pagos(datos, periodo, solo=None, excepto=(), monto=None):
    """
    Registra pagos de los cobros del período con Pago.registrar() (Issue #4), igual
    que lo haría el administrador: así el cobro pasa a PAGADO solo y el residente
    recibe su notificación. Unidades por "Torre-número", ej. "A-102".
    monto=None paga el total; un número registra un abono parcial.
    """
    fecha = date(periodo.anio, periodo.mes, calendar.monthrange(periodo.anio, periodo.mes)[1])
    medios = [Pago.Medio.TRANSFERENCIA, Pago.Medio.EFECTIVO, Pago.Medio.CHEQUE]  # para variar
    cobros = periodo.detalles.select_related("unidad__edificio").order_by("unidad__edificio__nombre", "unidad__numero")
    for i, cobro in enumerate(cobros):
        clave = f"{cobro.unidad.edificio.nombre[-1]}-{cobro.unidad.numero}"
        if (solo is None or clave in solo) and clave not in excepto:
            Pago.registrar(
                cobro, monto=monto or cobro.total, fecha=fecha, medio=medios[i % len(medios)],
                registrado_por=datos["usuarios"]["administrador"],
            )
