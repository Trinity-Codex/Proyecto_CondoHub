"""Consultas compartidas por la rendición mensual y el aviso de cobro."""
from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum

from apps.gastos.fondo import fin_mes, movimientos_fondo, saldo_fondo
from apps.gastos.models import Egreso, primer_dia_mes_siguiente
from apps.gastos.reportes import generar_reporte
from apps.pagos.models import Pago


def caja_del_mes(periodo):
    """Caja registrada por fecha del movimiento, incluso si se abona un cobro antiguo."""
    inicio = date(periodo.anio, periodo.mes, 1)
    fin = primer_dia_mes_siguiente(periodo.anio, periodo.mes)
    ingresos = Pago.objects.vigentes().filter(detalle__periodo__condominio=periodo.condominio)
    egresos = Egreso.objects.filter(periodo__condominio=periodo.condominio)

    def movimientos(consulta):
        return consulta.filter(fecha__lt=fin).aggregate(
            mes=Sum("monto", filter=Q(fecha__gte=inicio), default=0),
            acumulado=Sum("monto", default=0),
        )

    entradas, salidas = movimientos(ingresos), movimientos(egresos)
    return {"ingresos": entradas["mes"], "egresos": salidas["mes"],
            "saldo": entradas["acumulado"] - salidas["acumulado"]}


def saldo_fondo_del_periodo(periodo):
    try:
        return saldo_fondo(periodo.condominio, periodo)
    except ValidationError as error:
        if error.code not in {"fondo_sin_apertura", "fondo_sin_cobertura"}:
            raise
        return None


def rendicion_del_periodo(periodo):
    mes = (date(periodo.anio, periodo.mes, 1), fin_mes(periodo))
    pagos = Pago.objects.filter(detalle__periodo__condominio=periodo.condominio).select_related(
        "detalle__unidad__edificio", "detalle__periodo"
    )
    fondo = saldo_fondo_del_periodo(periodo)
    return {
        "caja": caja_del_mes(periodo),
        "pagos": pagos.vigentes().filter(fecha__range=mes).order_by("fecha", "pk"),
        "egresos": Egreso.objects.filter(periodo__condominio=periodo.condominio, fecha__range=mes)
            .select_related("proveedor").order_by("fecha", "pk"),
        "anulados": pagos.filter(anulado=True).filter(
            Q(fecha__range=mes) | Q(anulado_en__date__range=mes)
        ).order_by("fecha", "pk"),
        "reporte": generar_reporte(periodo),
        "saldo_fondo": fondo,
        "movimientos": movimientos_fondo(periodo.condominio, periodo) if fondo is not None else (),
    }
