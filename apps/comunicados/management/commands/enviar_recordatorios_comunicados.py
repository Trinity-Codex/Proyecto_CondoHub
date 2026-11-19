"""
Recuerda los comunicados sin leer (Issue #120). Ver apps/comunicados/recordatorios.py.

    python manage.py enviar_recordatorios_comunicados                     # hoy
    python manage.py enviar_recordatorios_comunicados --fecha 2026-11-25  # simula otro día

Pensado para correr una vez al día (cron, ver el despliegue #29). Correrlo más de una vez no
repite avisos.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.comunicados.recordatorios import enviar_recordatorios_comunicados


class Command(BaseCommand):
    help = "Recuerda a los residentes los comunicados que no han leído después del plazo de su condominio."

    def add_arguments(self, parser):
        parser.add_argument("--fecha", help="Día a simular, en formato AAAA-MM-DD. Por defecto, hoy.")

    def handle(self, *args, **opciones):
        if opciones["fecha"]:
            try:
                hoy = date.fromisoformat(opciones["fecha"])
            except ValueError:
                raise CommandError("La fecha debe tener el formato AAAA-MM-DD, por ejemplo 2026-11-25.") from None
        else:
            hoy = timezone.localdate()
        enviados = enviar_recordatorios_comunicados(hoy)
        self.stdout.write(self.style.SUCCESS(f"Recordatorios de comunicados del {hoy:%d-%m-%Y}: {enviados}."))
