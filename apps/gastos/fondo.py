"""Fondo de reserva y contrato C5. Saldo contable de aportes emitidos, distinto del efectivo recaudado."""
from calendar import monthrange
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.auditoria.servicios import Accion, registrar
from apps.condominios.models import Condominio

from .models import MONTO_MAXIMO, MovimientoFondo, PeriodoGasto, primer_dia_mes_siguiente


def fin_mes(periodo):
    return date(periodo.anio, periodo.mes, monthrange(periodo.anio, periodo.mes)[1])


def _validar_periodo(condominio, periodo):
    if condominio.pk is None or (periodo is not None and (periodo.pk is None or periodo.condominio_id != condominio.pk)):
        raise ValidationError("El período debe pertenecer al condominio guardado.")


def _legado(condominio):
    return PeriodoGasto.objects.filter(
        condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO, ingreso_fondo__isnull=True,
    ).order_by("-anio", "-mes").first()


def validar_cobertura(condominio, fecha=None):
    """Rechaza historia desconocida y fechas anteriores a la apertura."""
    inicial = MovimientoFondo.objects.filter(condominio=condominio, tipo=MovimientoFondo.Tipo.INICIAL).first()
    if inicial is None and _legado(condominio):
        raise ValidationError(
            "Configura el saldo inicial documentado: hay períodos emitidos sin cobertura del fondo.",
            code="fondo_sin_apertura",
        )
    if inicial and fecha is not None and fecha < inicial.fecha:
        raise ValidationError(
            f"Histórico del fondo no disponible. Hay cobertura desde el {inicial.fecha:%d-%m-%Y}.",
            code="fondo_sin_cobertura",
        )


def saldo_fondo(condominio, hasta_periodo=None):
    """C5: int en pesos; None suma todo, período guardado corta inclusivamente al fin de su mes.

    Rechaza período ajeno y legado sin apertura (fondo_sin_apertura) o corte anterior
    a ella (fondo_sin_cobertura). No consulta caja ni crea datos. Ejemplo ficticio:
    inicial 100000 + aporte de noviembre 5000 - egreso de noviembre 2000 = 103000,
    aunque se emita en diciembre; un egreso de diciembre queda fuera de noviembre.
    """
    _validar_periodo(condominio, hasta_periodo)
    corte = fin_mes(hasta_periodo) if hasta_periodo is not None else None
    validar_cobertura(condominio, corte)
    movimientos = MovimientoFondo.objects.filter(condominio=condominio)
    if corte is not None:
        movimientos = movimientos.filter(fecha__lte=corte)
    return int(movimientos.aggregate(total=Sum("monto"))["total"] or 0)


def movimientos_fondo(condominio, periodo=None):
    """C5: QuerySet de MovimientoFondo, orden fecha/pk y relaciones cargadas.

    None devuelve todo el libro; período guardado limita al mes contable inclusivo,
    sin exigir emisión. Mismos errores de pertenencia/cobertura que saldo_fondo.
    Cada objeto expone monto firmado, tipo, fecha, descripción, acuerdo y referencias.
    """
    _validar_periodo(condominio, periodo)
    corte = fin_mes(periodo) if periodo is not None else None
    validar_cobertura(condominio, corte)
    movimientos = MovimientoFondo.objects.filter(condominio=condominio).select_related("proveedor", "periodo", "creado_por")
    if periodo is not None:
        movimientos = movimientos.filter(fecha__range=(date(periodo.anio, periodo.mes, 1), corte))
    return movimientos.order_by("fecha", "pk")


def guardar_movimiento(movimiento, usuario):
    """Uso interno dentro de la transacción del servicio manual o de emisión."""
    movimiento.full_clean()
    movimiento.save()
    registrar(usuario, movimiento.condominio, Accion.CREAR, movimiento, despues={
        "tipo": movimiento.tipo, "monto": movimiento.monto, "fecha": movimiento.fecha,
        "descripcion": movimiento.descripcion, "acuerdo": movimiento.acuerdo,
        "proveedor_id": movimiento.proveedor_id, "periodo_id": movimiento.periodo_id,
    })
    return movimiento


@transaction.atomic
def registrar_movimiento(condominio, *, tipo, monto, fecha, descripcion, usuario=None, acuerdo="", proveedor=None, periodo=None):
    """Crea inicial, egreso (monto positivo) o ajuste firmado; valida y audita atómicamente."""
    condominio = Condominio.objects.select_for_update().get(pk=condominio.pk)
    if tipo not in (MovimientoFondo.Tipo.INICIAL, MovimientoFondo.Tipo.EGRESO, MovimientoFondo.Tipo.AJUSTE) or periodo is not None:
        raise ValidationError("Los ingresos solo se crean al emitir un período; los manuales no llevan período.")
    if type(monto) is not int or abs(monto) > MONTO_MAXIMO:
        raise ValidationError({"monto": f"Indica pesos enteros hasta {MONTO_MAXIMO}."})
    if (tipo == MovimientoFondo.Tipo.INICIAL and monto < 0) or (tipo == MovimientoFondo.Tipo.EGRESO and monto <= 0) or (tipo == MovimientoFondo.Tipo.AJUSTE and monto == 0):
        raise ValidationError({"monto": "Inicial no negativo, egreso positivo y ajuste distinto de cero."})
    movimiento = MovimientoFondo(
        condominio=condominio, tipo=tipo, monto=-monto if tipo == MovimientoFondo.Tipo.EGRESO else monto,
        fecha=fecha, descripcion=descripcion, acuerdo=acuerdo, proveedor=proveedor, creado_por=usuario,
        marca_inicial=1 if tipo == MovimientoFondo.Tipo.INICIAL else None,
    )
    movimiento.full_clean()
    fecha = movimiento.fecha
    if tipo == MovimientoFondo.Tipo.INICIAL:
        legado = _legado(condominio)
        if legado and fecha < primer_dia_mes_siguiente(legado.anio, legado.mes):
            raise ValidationError({"fecha": "La apertura debe ser posterior al último período legado."})
        primero = MovimientoFondo.objects.filter(condominio=condominio).first()
        if primero and fecha > primero.fecha:
            raise ValidationError({"fecha": "La apertura no puede ser posterior al primer movimiento existente."})
    else:
        validar_cobertura(condominio, fecha)
    return guardar_movimiento(movimiento, usuario)
