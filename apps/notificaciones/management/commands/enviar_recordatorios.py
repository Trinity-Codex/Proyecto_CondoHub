"""
Envía los recordatorios de pago del día (Issue #57). Ver apps/notificaciones/recordatorios.py.

    python manage.py enviar_recordatorios                     # hoy
    python manage.py enviar_recordatorios --fecha 2026-12-07  # simula otro día

Pensado para correr una vez al día en el servidor (cron, ver el despliegue #29).
Correrlo más de una vez el mismo día no repite avisos.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.notificaciones.models import RecordatorioEnviado
from apps.notificaciones.recordatorios import enviar_recordatorios


class Command(BaseCommand):
    help = "Avisa a los residentes con saldo antes y después del vencimiento de sus gastos comunes."

    def add_arguments(self, parser):
        parser.add_argument("--fecha", help="Día a simular, en formato AAAA-MM-DD. Por defecto, hoy.")

    def handle(self, *args, **opciones):
        if opciones["fecha"]:
            try:
                hoy = date.fromisoformat(opciones["fecha"])
            except ValueError:
                raise CommandError("La fecha debe tener el formato AAAA-MM-DD, por ejemplo 2026-12-07.")
        else:
            hoy = timezone.localdate()
        enviados = enviar_recordatorios(hoy)
        antes, despues = enviados[RecordatorioEnviado.Tipo.ANTES], enviados[RecordatorioEnviado.Tipo.DESPUES]
        self.stdout.write(
            self.style.SUCCESS(
                f"Recordatorios del {hoy:%d-%m-%Y}: {antes} antes del vencimiento y {despues} después del vencimiento."
            )
        )
