"""
Evolución del fondo de reserva (RQ-05, Issue #119). Solo lectura: no cambia dinero ni audita.

Todas las pantallas del fondo mes a mes (gráfico, tabla, edificios, unidades, residentes y la
vista del residente) salen de aquí, para que muestren los mismos números. Decisiones en
openspec/changes/agregar-evolucion-del-fondo-de-reserva/design.md:

  - El cierre de cada mes es la suma de los movimientos del libro hasta su último día:
    la misma regla de fondo.saldo_fondo(condominio, hasta_periodo) (contrato C5).
  - Un aporte es el monto_fondo_reserva de un cobro cuyo período ya entró al libro (tiene
    su ingreso). Los ítems de cobro (#117: monto_items, LineaCobro) NO aportan al fondo.
  - Saldo por edificio (consulta C4 pendiente): aportes de sus unidades más su parte, según
    la suma de sus alícuotas, de los movimientos del condominio (inicial, egresos, ajustes).
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.condominios.models import Edificio, Residente, Unidad
from apps.condominios.residencias import cobros_visibles

from .fondo import validar_cobertura
from .models import MESES, DetalleGastoComun, MovimientoFondo, PeriodoGasto
from .prorrateo import repartir

Tipo = MovimientoFondo.Tipo


@dataclass
class MesFondo:
    """Una fila de la evolución: lo que pasó en el fondo durante un mes contable."""

    anio: int
    mes: int
    apertura: int = 0  # cierre del mes anterior + saldo inicial registrado este mes
    aportes: int = 0  # ingresos de la emisión (aportes de las unidades)
    egresos: int = 0  # en positivo: lo que salió del fondo
    ajustes: int = 0  # con signo
    cierre: int = 0
    emitido: bool = False  # ¿hubo período emitido ese mes? Si no, no hay aporte que mostrar

    @property
    def nombre(self):
        return f"{MESES[self.mes - 1].capitalize()} {self.anio}"

    @property
    def corto(self):
        """Etiqueta del gráfico: "nov 26"."""
        return f"{MESES[self.mes - 1][:3]} {self.anio % 100:02d}"


def _siguiente(anio, mes):
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def serie_mensual(condominio, hoy=None):
    """
    Lista de MesFondo desde el mes del primer movimiento hasta el mes actual (o el último
    mes con movimientos, si es posterior). Lista vacía si el fondo no tiene movimientos.

    Lanza ValidationError (fondo_sin_apertura) si hay períodos emitidos sin saldo inicial:
    sin apertura no hay historia conocida y no se inventa una serie.
    """
    validar_cobertura(condominio)
    movimientos = list(
        MovimientoFondo.objects.filter(condominio=condominio).order_by("fecha", "pk").values_list("tipo", "monto", "fecha")
    )
    if not movimientos:
        return []
    totales = defaultdict(lambda: defaultdict(int))  # (año, mes) -> tipo -> suma
    for tipo, monto, fecha in movimientos:
        totales[(fecha.year, fecha.month)][tipo] += monto
    emitidos = set(
        PeriodoGasto.objects.filter(condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO).values_list("anio", "mes")
    )
    hoy = hoy or timezone.localdate()
    primero = movimientos[0][2]
    clave, fin = (primero.year, primero.month), max((hoy.year, hoy.month), max(totales))

    serie, saldo = [], 0
    while clave <= fin:
        del_mes = totales.get(clave, {})
        fila = MesFondo(
            anio=clave[0], mes=clave[1], apertura=saldo + del_mes.get(Tipo.INICIAL, 0),
            aportes=del_mes.get(Tipo.INGRESO, 0), egresos=-del_mes.get(Tipo.EGRESO, 0),
            ajustes=del_mes.get(Tipo.AJUSTE, 0), emitido=clave in emitidos,
        )
        fila.cierre = fila.apertura + fila.aportes - fila.egresos + fila.ajustes
        saldo = fila.cierre
        serie.append(fila)
        clave = _siguiente(*clave)
    return serie


# Medidas del gráfico en unidades del viewBox del SVG (se escala al ancho de la pantalla).
ALTO_GRAFICO = 180
PASO_BARRA = 48
ANCHO_BARRA = 32
MARGEN_SUPERIOR = 8
ALTO_ETIQUETAS = 24
ANCHO_MINIMO = 480  # con pocos meses, las barras se centran en este ancho en vez de estirarse


def grafico(serie):
    """
    Geometría de las barras del saldo de cierre, una por mes de la serie y con el MISMO valor
    que la tabla. Soporta saldos negativos: las barras bajan desde la línea de cero.
    """
    if not serie:
        return None
    maximo = max(0, *(fila.cierre for fila in serie))
    minimo = min(0, *(fila.cierre for fila in serie))
    rango = (maximo - minimo) or 1
    cero = MARGEN_SUPERIOR + ALTO_GRAFICO * maximo / rango
    # Con muchos meses, las etiquetas no caben todas: se muestra una de cada "salto".
    salto = max(1, -(-len(serie) // 12))
    ancho = max(len(serie) * PASO_BARRA, ANCHO_MINIMO)
    margen = (ancho - len(serie) * PASO_BARRA) / 2
    barras = []
    for i, fila in enumerate(serie):
        alto = ALTO_GRAFICO * abs(fila.cierre) / rango
        barras.append({
            "fila": fila,
            "x": margen + i * PASO_BARRA + (PASO_BARRA - ANCHO_BARRA) / 2,
            "centro": margen + i * PASO_BARRA + PASO_BARRA / 2,
            "y": cero - alto if fila.cierre >= 0 else cero,
            "alto": max(alto, 1),  # un saldo cero se ve como una línea, no desaparece
            "etiqueta": fila.corto if i % salto == 0 else "",
        })
    alto_total = MARGEN_SUPERIOR + ALTO_GRAFICO + ALTO_ETIQUETAS
    return {
        "ancho": ancho, "ancho_barra": ANCHO_BARRA, "ancho_barras": len(serie) * PASO_BARRA, "alto": alto_total, "cero": cero,
        "y_etiquetas": alto_total - 6, "barras": barras,
    }


def cobros_con_aporte(condominio):
    """Cobros cuyo aporte entró al libro del fondo (período emitido con su ingreso)."""
    return DetalleGastoComun.objects.filter(
        periodo__condominio=condominio, periodo__estado=PeriodoGasto.Estado.EMITIDO, periodo__ingreso_fondo__isnull=False,
    )


def por_edificio(condominio, serie):
    """
    Aportes de cada edificio por mes emitido y saldo por edificio (ver el docstring del módulo).
    Devuelve {"edificios", "meses": [(MesFondo, [aporte por edificio], total)],
    "filas": [{edificio, aporte, parte, saldo}], "sin_alicuotas"}. Los saldos suman el cierre
    del último mes; sin alícuotas no se puede repartir y parte y saldo quedan en None.
    """
    edificios = list(Edificio.objects.filter(condominio=condominio).order_by("nombre", "pk"))
    alicuotas = dict(
        Unidad.objects.filter(edificio__condominio=condominio).values("edificio").annotate(s=Sum("alicuota")).values_list("edificio", "s")
    )
    por_mes = defaultdict(dict)
    filas = cobros_con_aporte(condominio).values("periodo__anio", "periodo__mes", "unidad__edificio").annotate(s=Sum("monto_fondo_reserva"))
    for fila in filas:
        por_mes[(fila["periodo__anio"], fila["periodo__mes"])][fila["unidad__edificio"]] = fila["s"]

    meses = []
    for mes in serie:
        if (mes.anio, mes.mes) in por_mes:
            montos = [por_mes[(mes.anio, mes.mes)].get(e.pk, 0) for e in edificios]
            meses.append((mes, montos, sum(montos)))
    aportes = [sum(montos[i] for _, montos, _ in meses) for i in range(len(edificios))]

    # Lo que no es aporte (inicial, egresos y ajustes) es del condominio: se reparte por alícuota.
    cierre = serie[-1].cierre if serie else 0
    otros = cierre - sum(aportes)
    pesos = {e: alicuotas.get(e.pk) or Decimal("0") for e in edificios}
    sin_alicuotas = otros != 0 and sum(pesos.values(), Decimal("0")) <= 0
    reparto = repartir(abs(otros), pesos)
    signo = -1 if otros < 0 else 1
    filas_edificios = []
    for edificio, aporte in zip(edificios, aportes):
        parte = None if sin_alicuotas else signo * reparto[edificio]
        filas_edificios.append({
            "edificio": edificio, "aporte": aporte, "parte": parte,
            "saldo": None if parte is None else aporte + parte,
        })
    return {"edificios": edificios, "meses": meses, "filas": filas_edificios, "sin_alicuotas": sin_alicuotas}


def _en_residencia(residencia, anio, mes):
    """Misma regla de superposición por mes que residencias.cobros_visibles (#46)."""
    if (residencia.desde.year, residencia.desde.month) > (anio, mes):
        return False
    return residencia.hasta is None or (residencia.hasta.year, residencia.hasta.month) >= (anio, mes)


def por_unidad(condominio):
    """
    Aporte acumulado de cada unidad y de cada residente vigente en los meses que se superponen
    con su período de residencia. Para el administrador y el comité. Las residencias dadas de
    baja no se listan: la pantalla de unidades tampoco muestra a quien ya no vive ahí.
    """
    unidades = list(Unidad.objects.filter(edificio__condominio=condominio).select_related("edificio").order_by("edificio__nombre", "numero"))
    cobros = defaultdict(list)  # unidad_id -> [(año, mes, aporte)]
    for unidad_id, anio, mes, aporte in cobros_con_aporte(condominio).values_list(
        "unidad", "periodo__anio", "periodo__mes", "monto_fondo_reserva"
    ):
        cobros[unidad_id].append((anio, mes, aporte))
    filas_unidades = [{"unidad": u, "aporte": sum(a for _, _, a in cobros[u.pk])} for u in unidades]
    residencias = (
        Residente.objects.filter(unidad__edificio__condominio=condominio, activo=True)
        .select_related("usuario", "unidad__edificio")
        .order_by("unidad__edificio__nombre", "unidad__numero", "desde", "pk")
    )
    filas_residentes = [
        {"residencia": r, "aporte": sum(a for anio, mes, a in cobros[r.unidad_id] if _en_residencia(r, anio, mes))}
        for r in residencias
    ]
    return {"unidades": filas_unidades, "residentes": filas_residentes, "total": sum(f["aporte"] for f in filas_unidades)}


def aportes_de_unidad(unidad, usuario=None):
    """
    Aportes mes a mes de una unidad, del más reciente al más antiguo. Con usuario, solo los
    meses de su residencia activa en la unidad (#46), como ve el residente sus cobros.
    """
    cobros = cobros_con_aporte(unidad.edificio.condominio).filter(unidad=unidad)
    if usuario is not None:
        cobros = cobros_visibles(cobros, usuario)
    return list(cobros.select_related("periodo").order_by("-periodo__anio", "-periodo__mes"))


def unidades_del_residente(usuario, condominio):
    """Unidades del condominio donde el usuario es residente activo."""
    return list(
        Unidad.objects.filter(edificio__condominio=condominio, residentes__usuario=usuario, residentes__activo=True)
        .select_related("edificio").order_by("edificio__nombre", "numero").distinct()
    )
