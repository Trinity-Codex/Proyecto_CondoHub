"""
Datos demo de gastos comunes (Issues #1, #2 y #62), en Vista Verde:
  - hace DOS meses: emitido;
  - mes ANTERIOR: emitido;
  - mes ACTUAL: abierto, con egresos, listo para probar la emisión.
Los pagos de los meses emitidos los registra apps/pagos/demo.py.

Deja en datos["periodos"] los tres períodos: "hace_dos_meses", "anterior" y "actual".
"""
from datetime import date, timedelta

from apps.gastos.models import Egreso, PeriodoGasto
from apps.gastos.servicios import emitir_periodo


def cargar(datos):
    hoy = date.today()
    mes_anterior = hoy.replace(day=1) - timedelta(days=1)  # último día del mes anterior
    hace_dos_meses = mes_anterior.replace(day=1) - timedelta(days=1)

    antiguo = _periodo_con_egresos(datos, hace_dos_meses, ajuste=1.02)
    emitir_periodo(antiguo)
    anterior = _periodo_con_egresos(datos, mes_anterior, ajuste=0.97)
    emitir_periodo(anterior)
    actual = _periodo_con_egresos(datos, hoy)
    datos["periodos"] = {"hace_dos_meses": antiguo, "anterior": anterior, "actual": actual}


def _periodo_con_egresos(datos, fecha, ajuste=1.0):
    """Crea el período del mes de "fecha" con egresos típicos (ajuste: para variar los montos)."""
    proveedores = datos.get("proveedores", {})
    administrador = datos["usuarios"]["administrador"]
    periodo = PeriodoGasto.objects.create(condominio=datos["vista_verde"], anio=fecha.year, mes=fecha.month)
    C = Egreso.Categoria
    # El 4.º dato es el proveedor (clave del diccionario) o None si no corresponde (sueldos, cuentas básicas).
    egresos = [
        (C.REMUNERACIONES, "Sueldo conserje (jornada completa)", 650000, None),
        (C.REMUNERACIONES, "Sueldo personal de aseo", 520000, None),
        (C.CONSUMOS, "Electricidad áreas comunes", 185430, None),
        (C.CONSUMOS, "Agua áreas comunes y riego", 96780, None),
        (C.MANTENCION, "Mantención mensual de ascensores", 240000, "ascensores"),
        (C.ASEO, "Artículos de aseo", 48990, "aseo"),
        (C.SEGURIDAD, "Monitoreo de cámaras", 75000, "seguridad"),
        (C.ADMINISTRACION, "Honorarios de administración", 350000, None),
    ]
    for dia, (categoria, descripcion, monto, clave_proveedor) in enumerate(egresos, start=1):
        Egreso.objects.create(
            periodo=periodo, categoria=categoria, descripcion=descripcion, monto=round(monto * ajuste),
            fecha=fecha.replace(day=min(dia, fecha.day)), creado_por=administrador,
            proveedor=proveedores.get(clave_proveedor),
        )
    return periodo
