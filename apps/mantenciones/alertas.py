"""
Alertas de vencimiento de mantenciones (Issue #123, RQ-08).

Avisa por la campana y por correo (patrón Observer, igual que los recordatorios de pago #57) a los
administradores del condominio cuando una mantención entra en su ventana de alerta (`dias_anticipacion`)
o ya venció sin haberse hecho. Ninguna mantención vence sin un aviso previo.

  - Un aviso por mantención y por fecha de vencimiento: AlertaEnviada lo impide aunque el comando corra
    varias veces. Al registrar una ejecución la fecha cambia y el ciclo siguiente avisa de nuevo.
  - Solo condominios activos y administradores activos del propio condominio.

Uso: python manage.py enviar_alertas_mantenciones [--fecha AAAA-MM-DD]
En la demo de Render no hay tareas programadas: se ejecuta a mano. En producción lo programa #29.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.urls import reverse

from apps.condominios.models import Membresia
from apps.notificaciones.observador import Evento, Sujeto

from .models import AlertaEnviada, Mantencion

logger = logging.getLogger(__name__)


class Alerta(Sujeto):
    """Sujeto del Observer para las alertas de mantención: no es un modelo, solo avisa (ver apps.py)."""


def mantenciones_por_atender(condominio, hoy):
    """Mantenciones del condominio por vencer o vencidas hoy, de la más urgente a la menos (para el panel)."""
    candidatas = Mantencion.objects.filter(condominio=condominio).order_by("proxima_fecha", "nombre", "pk")
    return [m for m in candidatas if m.estado_en(hoy) != Mantencion.Estado.AL_DIA]


# @spec:mantenciones-alertas-de-vencimiento
def alertas_pendientes(hoy):
    """Mantenciones que hay que avisar hoy y aún no se avisaron para su fecha actual. No guarda nada."""
    # Cota gruesa en la base (la anticipación máxima es 365 días); el estado exacto se decide en Python.
    candidatas = (
        Mantencion.objects.filter(condominio__activo=True, proxima_fecha__lte=hoy + timedelta(days=365))
        .select_related("condominio")
        .order_by("proxima_fecha", "pk")
    )
    ya_avisadas = set(AlertaEnviada.objects.values_list("mantencion_id", "fecha_objetivo"))
    return [
        m for m in candidatas
        if m.estado_en(hoy) != Mantencion.Estado.AL_DIA and (m.pk, m.proxima_fecha) not in ya_avisadas
    ]


def evento_para(mantencion, administradores, hoy):
    vence = mantencion.proxima_fecha.strftime("%d-%m-%Y")
    if mantencion.proxima_fecha < hoy:
        titulo = f"Mantención vencida: {mantencion.nombre}"
        mensaje = f"«{mantencion.nombre}» venció el {vence}. Regístrala cuando se haga."
    else:
        titulo = f"Mantención por vencer: {mantencion.nombre}"
        mensaje = f"«{mantencion.nombre}» vence el {vence}."
    return Evento(
        condominio=mantencion.condominio,
        titulo=titulo,
        mensaje=mensaje,
        destinatarios=administradores,
        url=reverse("mantenciones:lista"),
    )


# @spec:mantenciones-alertas-de-vencimiento
def enviar_alertas(hoy):
    """Envía las alertas que corresponden hoy. Devuelve cuántas mantenciones se avisaron."""
    pendientes = alertas_pendientes(hoy)
    if not pendientes:
        return 0
    administradores = {}  # condominio_id -> usuarios activos con rol de administrador
    for membresia in Membresia.objects.filter(
        condominio__in={m.condominio_id for m in pendientes}, rol=Membresia.Rol.ADMINISTRADOR,
        activo=True, usuario__is_active=True,
    ).select_related("usuario"):
        administradores.setdefault(membresia.condominio_id, []).append(membresia.usuario)

    enviadas = 0
    for mantencion in pendientes:
        destinatarios = administradores.get(mantencion.condominio_id, [])
        if not destinatarios:
            continue  # sin a quién avisar no se deja constancia: el aviso sale cuando haya un administrador activo
        try:
            with transaction.atomic():
                # Primero la constancia: si otra ejecución ya la creó (get_or_create resuelve la carrera con la
                # restricción única), se omite este aviso. Si notificar falla, la constancia se deshace y se reintenta.
                _, creada = AlertaEnviada.objects.get_or_create(
                    mantencion=mantencion, fecha_objetivo=mantencion.proxima_fecha
                )
                if not creada:
                    continue
                Alerta().notificar(evento_para(mantencion, destinatarios, hoy))
        except Exception:  # noqa: BLE001 - un fallo en una mantención no debe frenar los avisos de las demás
            logger.exception("No se pudo avisar la mantención %s (vence %s)", mantencion.pk, mantencion.proxima_fecha)
            continue
        enviadas += 1
    return enviadas
