"""
Datos demo de pagos (Issues #4, #5 y #62), sobre los períodos emitidos de apps/gastos/demo.py:
  - hace dos meses: pagaron todos menos A-102 y B-202 (quedan morosas);
  - mes anterior: la mitad pagó, B-201 hizo un abono PARCIAL y el resto debe
    (sirve para el estado de cuenta, la cobranza y el reporte).
Cada pago se fecha el último día del mes de su período.
Solo en la demo del cliente (hay "fecha_referencia_demo"), Los Aromos también tiene pagos (Issue #98).
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
    if "fecha_referencia_demo" in datos:
        _pagos_los_aromos(datos)


def _pagos_los_aromos(datos):
    """
    Issue #98: Los Aromos llega a la demo del cliente con un cobro de cada tipo, para que la
    cartera muestre pagado, parcial y pendiente. La carga normal no pasa por aquí: su huella no cambia.
    La clave es "o-NÚMERO" porque su único edificio se llama "Edificio único" (ver _registrar_pagos).
    El período es el mes anterior a la fecha de referencia, así que su fecha de pago (fin de ese mes)
    nunca es posterior a ella. Pago.registrar no toca el fondo de reserva: el aporte ya entró al emitir.
    """
    aromos = datos["periodos"]["los_aromos"]
    _registrar_pagos(datos, aromos, solo=["o-101", "o-102"])  # pagan el total
    _registrar_pagos(datos, aromos, solo=["o-201"], monto=60000)  # abono parcial; o-202 queda pendiente


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
