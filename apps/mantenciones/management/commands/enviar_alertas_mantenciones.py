"""
Envía las alertas de mantenciones por vencer o vencidas (Issue #123). Ver apps/mantenciones/alertas.py.

    python manage.py enviar_alertas_mantenciones                     # hoy
    python manage.py enviar_alertas_mantenciones --fecha 2026-12-07  # simula otro día

Correrlo más de una vez el mismo día no repite avisos.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.mantenciones.alertas import enviar_alertas


class Command(BaseCommand):
    help = "Avisa a los administradores de las mantenciones por vencer o vencidas."

    def add_arguments(self, parser):
        parser.add_argument("--fecha", help="Día a simular, en formato AAAA-MM-DD. Por defecto, hoy.")

    def handle(self, *args, **opciones):
        if opciones["fecha"]:
            try:
                hoy = date.fromisoformat(opciones["fecha"])
            except ValueError:
                raise CommandError("La fecha debe tener el formato AAAA-MM-DD, por ejemplo 2026-12-07.") from None
        else:
            hoy = timezone.localdate()
        enviadas = enviar_alertas(hoy)
        self.stdout.write(self.style.SUCCESS(f"Alertas de mantenciones del {hoy:%d-%m-%Y}: {enviadas} enviadas."))
