"""
Recordatorio de comunicados sin leer (Issue #120, RQ-04).

Avisa por la campana y por correo (patrón Observer, igual que los recordatorios de pago de #57)
a cada residente que no leyó un comunicado vigente dirigido a él, cuando pasaron N días desde
la publicación. N se configura por condominio (AjustesComunicados, por defecto 3).

  - Una sola vez por comunicado y persona: RecordatorioComunicado lo impide aunque el comando
    corra varias veces.
  - Ventana de 7 días después del plazo: si el comando no corrió un día, igual avisa; un
    comunicado viejo (por ejemplo, el de bienvenida de hace meses) no dispara avisos al activar
    esta función.
  - Solo comunicados vigentes, condominios activos y cuentas activas. No avisa al comité ni a
    quien ya lo leyó.

Uso: python manage.py enviar_recordatorios_comunicados [--fecha AAAA-MM-DD]
En la demo de Render no hay tareas programadas: se ejecuta a mano. En producción lo programa #29.
"""
from datetime import datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notificaciones.observador import Evento, Sujeto

from .models import AjustesComunicados, Comunicado, LecturaComunicado, RecordatorioComunicado

VENTANA_DIAS = 7


class RecordatorioLectura(Sujeto):
    """Sujeto del Observer para los recordatorios de lectura (ver apps/notificaciones/apps.py)."""


def avisos_pendientes(hoy):
    """Lista de (comunicado, usuario) que corresponde recordar hoy y que aún no se recordaron."""
    avisos = []
    # Límite como fecha y hora local (no __date): MySQL sin tablas de zonas horarias no resuelve
    # __date con USE_TZ (ver #128). Publicados antes de hoy y dentro del plazo más largo posible.
    inicio_de_hoy = timezone.make_aware(datetime.combine(hoy, time.min))
    comunicados = (
        Comunicado.objects.filter(condominio__activo=True)
        .vigentes(hoy)
        .filter(
            fecha_publicacion__lt=inicio_de_hoy,
            fecha_publicacion__gte=inicio_de_hoy - timedelta(days=30 + VENTANA_DIAS),
        )
        .select_related("condominio", "edificio")
    )
    dias_por_condominio = {}
    for comunicado in comunicados:
        condominio = comunicado.condominio
        if condominio.pk not in dias_por_condominio:
            dias_por_condominio[condominio.pk] = AjustesComunicados.dias_de(condominio)
        dias = dias_por_condominio[condominio.pk]
        desde_publicacion = (hoy - timezone.localdate(comunicado.fecha_publicacion)).days
        if not dias <= desde_publicacion <= dias + VENTANA_DIAS:
            continue
        leyeron = set(LecturaComunicado.objects.filter(comunicado=comunicado).values_list("usuario_id", flat=True))
        recordados = set(comunicado.recordatorios.values_list("usuario_id", flat=True))
        residentes = comunicado.residentes_destinatarios().filter(usuario__is_active=True).select_related("usuario")
        vistos = set()
        for residente in residentes:
            usuario = residente.usuario
            if usuario.pk in leyeron or usuario.pk in recordados or usuario.pk in vistos:
                continue
            vistos.add(usuario.pk)
            avisos.append((comunicado, usuario))
    return avisos


def enviar_recordatorios_comunicados(hoy):
    """Envía los recordatorios del día y devuelve cuántos se enviaron."""
    enviados = 0
    for comunicado, usuario in avisos_pendientes(hoy):
        try:
            with transaction.atomic():
                # Primero la constancia: si otro proceso ya la guardó, no se repite el aviso.
                RecordatorioComunicado.objects.create(comunicado=comunicado, usuario=usuario)
                RecordatorioLectura().notificar(
                    Evento(
                        condominio=comunicado.condominio,
                        titulo="Tienes un comunicado sin leer",
                        mensaje=comunicado.titulo,
                        destinatarios=[usuario],
                        url=comunicado.get_absolute_url(),
                        asunto=f"Recordatorio: {comunicado.titulo}",
                    )
                )
        except IntegrityError:
            continue
        enviados += 1
    return enviados
