"""
Carga datos de demostración para probar CondoHub.

Uso:
    python manage.py cargar_demo              # carga los datos (si no existen)
    python manage.py cargar_demo --reiniciar  # borra los datos demo y los vuelve a crear

Crea:
  - 2 condominios: "Condominio Vista Verde" (el del Informe 2) y "Edificio Los Aromos",
    para mostrar que la plataforma es multi-condominio.
  - 1 usuario por rol (todos con la clave CLAVE_DEMO, ver tabla en README.md).
  - Edificios y unidades con alícuotas que suman 1, espacios comunes,
    comunicados, incidentes, reservas y gastos comunes (dos meses emitidos, con pagos totales
    y parciales y unidades morosas, y el mes actual abierto; Los Aromos, con el mes anterior emitido).
  - 1 administrador general, gerencia@condohub.cl, con los dos condominios en su cartera (Issue #54).

Cada app tiene sus datos en apps/<app>/demo.py, con una función cargar(datos) (Issue #62).
Este comando solo las llama en orden, dentro de una transacción. "datos" es un diccionario
que cada app completa con lo que las siguientes necesitan: "usuarios", "vista_verde",
"los_aromos", "unidades", "proveedores" y "periodos". Para agregar datos demo de tu módulo,
edita el demo.py de tu app: no hace falta tocar este archivo.
"""
from importlib import import_module

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.condominios.demo import NOMBRES_DEMO
from apps.condominios.models import Condominio
from apps.cuentas.demo import CLAVE_DEMO, USUARIOS

# Orden de carga: cada app usa lo que dejaron las anteriores (ej. gastos usa los proveedores).
APPS_DEMO = [
    "cuentas", "condominios", "reservas", "comunicados", "incidentes",
    "proveedores", "gastos", "pagos", "notificaciones",
    "auditoria", "privacidad", "cartera", "rendicion",
]


class Command(BaseCommand):
    help = "Carga datos de demostración (condominios, usuarios por rol, espacios, comunicados...)."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra los datos demo y los crea de nuevo.")

    @transaction.atomic  # todo o nada: si algo falla, no queda la base a medias
    def handle(self, *args, **opciones):
        if Condominio.objects.filter(nombre__in=NOMBRES_DEMO).exists():
            if not opciones["reiniciar"]:
                self.stdout.write(self.style.WARNING(
                    "Los datos demo ya existen. Usa --reiniciar para borrarlos y crearlos de nuevo."
                ))
                return
            # Borrar el condominio borra en cascada edificios, unidades, comunicados, etc.
            Condominio.objects.filter(nombre__in=NOMBRES_DEMO).delete()

        datos = {}
        for app in APPS_DEMO:
            import_module(f"apps.{app}.demo").cargar(datos)

        vista_verde = datos["vista_verde"]
        self.stdout.write(self.style.SUCCESS("Datos demo cargados."))
        self.stdout.write(f"Clave de todos los usuarios demo: {CLAVE_DEMO}")
        for correo, *_ in USUARIOS.values():
            self.stdout.write(f"  - {correo}")
        # El administrador general (Issue #54) no está en USUARIOS: lo crea apps/cartera/demo.py.
        self.stdout.write(f"  - {datos['usuarios']['gerencia'].email} (administrador general: cartera de los dos condominios)")
        self.stdout.write(f"Suma de alícuotas de {vista_verde}: {vista_verde.suma_alicuotas()}")
