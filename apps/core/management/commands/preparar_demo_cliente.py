"""Prepara exclusivamente la SQLite local de demostración, sin regenerarla."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Migra y carga datos ficticios solo en la SQLite de .demo_cliente/."
    # La validación de aislamiento debe preceder incluso a los chequeos de Django.
    requires_system_checks = []

    def handle(self, *args, **opciones):
        configuracion = connections["default"].settings_dict
        error = "La demo requiere SQLite en una ruta absoluta dentro de .demo_cliente/."
        if configuracion["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError(error)
        directorio = Path(settings.BASE_DIR).resolve() / ".demo_cliente"
        nombre = Path(configuracion["NAME"])
        try:
            ruta = nombre.resolve()
            if (not nombre.is_absolute() or directorio.resolve() != directorio
                    or not ruta.is_relative_to(directorio) or ruta == directorio or ruta.is_dir()):
                raise CommandError(error)
        except (OSError, ValueError) as exc:
            raise CommandError(error) from exc

        self.stdout.write(f"Datos ficticios · motor: {configuracion['ENGINE']} · base: {ruta}")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        call_command("migrate", database="default", interactive=False,
                     stdout=self.stdout, stderr=self.stderr)
        call_command("cargar_demo", stdout=self.stdout, stderr=self.stderr)
        self.stdout.write(self.style.SUCCESS("Demo local preparada; se conservan los datos ficticios existentes."))
