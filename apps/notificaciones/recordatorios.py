"""
Recordatorios de pago (Issue #57, NTI-04).

Avisa por la campana y por correo (patrón Observer) a los residentes con saldo en un
período emitido:
  - ANTES:   entre 3 y 1 días antes del vencimiento;
  - DESPUÉS: entre 1 y 7 días después del vencimiento.
El día del vencimiento no se envía nada (ya llegó el aviso previo). Se usan ventanas y
no días exactos para cubrir un día en que el comando no corrió; RecordatorioEnviado
evita que el mismo aviso llegue dos veces.

No avisa a quien ya pagó ni a residentes fuera de su período de residencia (C2, #46).
Quien no quiere correos recibe solo la campana (lo decide NotificadorCorreo).

Uso: python manage.py enviar_recordatorios [--fecha AAAA-MM-DD]
"""
from collections import Counter
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.condominios.models import Residente
from apps.condominios.residencias import cobros_visibles
from apps.core.templatetags.condohub import pesos
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.pagos.consultas import saldo_del_cobro

from .models import RecordatorioEnviado
from .observador import Evento, Sujeto

DIAS_ANTES = 3    # se avisa desde 3 días antes del vencimiento...
DIAS_DESPUES = 7  # ...y hasta 7 días después


class Recordatorio(Sujeto):
    """Sujeto del Observer para los recordatorios: no es un modelo, solo avisa (ver apps.py)."""


def tipo_de_aviso(vencimiento, hoy):
    """ANTES, DESPUES o None según cuántos días faltan o pasaron desde el vencimiento."""
    dias = (vencimiento - hoy).days
    if 1 <= dias <= DIAS_ANTES:
        return RecordatorioEnviado.Tipo.ANTES
    if 1 <= -dias <= DIAS_DESPUES:
        return RecordatorioEnviado.Tipo.DESPUES
    return None


def evento_para(cobro, usuario, saldo, tipo):
    periodo = cobro.periodo
    vence = periodo.fecha_vencimiento.strftime("%d-%m-%Y")
    if tipo == RecordatorioEnviado.Tipo.ANTES:
        titulo = f"Tus gastos comunes de {periodo} vencen el {vence}"
        mensaje = f"Unidad {cobro.unidad}: tienes {pesos(saldo)} por pagar. Vence el {vence}."
    else:
        titulo = f"Tus gastos comunes de {periodo} están vencidos"
        mensaje = f"Unidad {cobro.unidad}: tienes {pesos(saldo)} por pagar. Venció el {vence}."
    return Evento(
        condominio=periodo.condominio,
        titulo=titulo,
        mensaje=mensaje,
        destinatarios=[usuario],
        url=reverse("pagos:cobro_detalle", args=[cobro.pk]),
    )


def avisos_pendientes(hoy):
    """
    Lista de (cobro, usuario, saldo, tipo) que corresponde avisar hoy y que aún no se
    avisaron. No guarda nada.
    """
    # 1) Períodos emitidos con el vencimiento dentro de alguna ventana.
    #    Solo de condominios activos: a uno desactivado ya no se puede entrar.
    periodos = PeriodoGasto.objects.filter(
        estado=PeriodoGasto.Estado.EMITIDO,
        condominio__activo=True,
        fecha_vencimiento__range=(hoy - timedelta(days=DIAS_DESPUES), hoy + timedelta(days=DIAS_ANTES)),
    )
    tipos = {p.pk: tipo_de_aviso(p.fecha_vencimiento, hoy) for p in periodos}
    tipos = {pk: tipo for pk, tipo in tipos.items() if tipo}
    if not tipos:
        return []

    # 2) Sus cobros con saldo (un pago parcial deja saldo).
    cobros = (
        DetalleGastoComun.objects.filter(periodo__in=list(tipos))
        .exclude(estado=DetalleGastoComun.Estado.PAGADO)
        .select_related("periodo__condominio", "unidad__edificio")
        .prefetch_related("pagos")
    )
    saldos = {c.pk: (c, saldo_del_cobro(c)) for c in cobros}
    saldos = {pk: (c, s) for pk, (c, s) in saldos.items() if s > 0}
    if not saldos:
        return []

    # 3) Residentes activos de esas unidades; cobros_visibles (C2) deja a cada uno solo
    #    los cobros de su período de residencia.
    residentes = Residente.objects.filter(
        unidad__in={c.unidad_id for c, _ in saldos.values()}, activo=True, usuario__is_active=True
    ).select_related("usuario")
    usuarios = {r.usuario_id: r.usuario for r in residentes}
    con_saldo = DetalleGastoComun.objects.filter(pk__in=list(saldos))
    ya_avisados = set(
        RecordatorioEnviado.objects.filter(cobro__in=list(saldos)).values_list("cobro_id", "usuario_id", "tipo")
    )

    avisos = []
    for usuario in usuarios.values():
        for cobro_id in cobros_visibles(con_saldo, usuario).values_list("pk", flat=True):
            cobro, saldo = saldos[cobro_id]
            tipo = tipos[cobro.periodo_id]
            if (cobro_id, usuario.pk, tipo) not in ya_avisados:  # 4) sin repetir
                avisos.append((cobro, usuario, saldo, tipo))
    return avisos


def enviar_recordatorios(hoy):
    """Envía los avisos que corresponden hoy. Devuelve cuántos se enviaron de cada tipo."""
    enviados = Counter()
    for cobro, usuario, saldo, tipo in avisos_pendientes(hoy):
        try:
            with transaction.atomic():
                # Primero la constancia: si otra ejecución ya la creó, la restricción única
                # lo impide y este aviso se omite (no se notifica dos veces).
                RecordatorioEnviado.objects.create(cobro=cobro, usuario=usuario, tipo=tipo)
                Recordatorio().notificar(evento_para(cobro, usuario, saldo, tipo))
        except IntegrityError:
            continue
        enviados[tipo] += 1
    return enviados
