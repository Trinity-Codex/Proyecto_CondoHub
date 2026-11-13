"""Aislamiento y contrato de los datos ficticios del Issue #93."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.db.models import Sum
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.condominios.models import Condominio
from apps.core import tests as pruebas_core
from apps.cuentas.models import Usuario
from config import settings_demo
from apps.gastos.fondo import movimientos_fondo, saldo_fondo
from apps.gastos.models import MovimientoFondo, PeriodoGasto


class PrepararDemoClienteTest(SimpleTestCase):
    def test_preparar_demo_rechaza_base_ajena_sin_escrituras(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            casos = [
                ("django.db.backends.mysql", base / ".demo_cliente/demo.sqlite3"),
                ("django.db.backends.sqlite3", base / "db.sqlite3"),
                ("django.db.backends.sqlite3", base / ".demo_cliente/../db.sqlite3"),
                ("django.db.backends.sqlite3", base / ".demo_cliente_ajena/demo.sqlite3"),
                ("django.db.backends.sqlite3", ":memory:"),
                ("django.db.backends.sqlite3", ""),
                ("django.db.backends.sqlite3", ".demo_cliente/demo.sqlite3"),
                ("django.db.backends.sqlite3", base / ".demo_cliente"),
            ]
            for motor, nombre in casos:
                with self.subTest(motor=motor, nombre=nombre), override_settings(BASE_DIR=base):
                    configuracion = {"ENGINE": motor, "NAME": nombre}
                    with patch.object(connections["default"], "settings_dict", configuracion):
                        with patch("apps.core.management.commands.preparar_demo_cliente.call_command") as escribir:
                            with self.assertRaisesRegex(CommandError, "SQLite.*[.]demo_cliente"):
                                call_command("preparar_demo_cliente", stdout=StringIO())
                            escribir.assert_not_called()
                    self.assertEqual(list(base.iterdir()), [])

    def test_preparar_demo_rechaza_enlaces_fuera_del_directorio(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            ajeno = base / "desarrollo"
            ajeno.mkdir()
            demo = base / ".demo_cliente"
            try:
                demo.symlink_to(ajeno, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"El sistema no permite enlaces simbólicos: {exc}")
            with override_settings(BASE_DIR=base), patch.object(
                connections["default"], "settings_dict",
                {"ENGINE": "django.db.backends.sqlite3", "NAME": demo / "demo.sqlite3"},
            ):
                with self.assertRaisesRegex(CommandError, "SQLite.*[.]demo_cliente"):
                    call_command("preparar_demo_cliente", stdout=StringIO())
            self.assertEqual(list(ajeno.iterdir()), [])

    def test_preparar_demo_no_duplica(self):
        codigo = textwrap.dedent('''
            import json
            import sys
            from pathlib import Path
            import django
            from django.conf import settings
            settings.BASE_DIR = Path(sys.argv[1])
            settings.DATABASES = {"default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": settings.BASE_DIR / ".demo_cliente/demo.sqlite3",
            }}
            settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
            django.setup()
            from django.apps import apps
            from django.core.management import call_command
            from apps.core.tests import huella_demo
            from apps.gastos.models import PeriodoGasto
            call_command("preparar_demo_cliente")
            antes = {m._meta.label: list(m.objects.order_by("pk").values())
                     for m in apps.get_models()}
            call_command("preparar_demo_cliente")
            despues = {m._meta.label: list(m.objects.order_by("pk").values())
                       for m in apps.get_models()}
            print("RESULTADO=" + json.dumps({
                "sin_cambios": antes == despues,
                "huella": huella_demo(),
                "periodos": list(PeriodoGasto.objects.order_by("condominio_id", "mes")
                                 .values_list("anio", "mes", "estado")),
            }, default=str))
        ''')
        with tempfile.TemporaryDirectory() as temporal:
            resultado = subprocess.run(
                [sys.executable, "-c", codigo, temporal],
                cwd=settings.BASE_DIR, env={**os.environ,
                    "DJANGO_SETTINGS_MODULE": "config.settings_demo", "PYTHONIOENCODING": "utf-8"},
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            datos = json.loads(resultado.stdout.split("RESULTADO=")[-1])
            self.assertTrue(datos["sin_cambios"])
            self.assertEqual(datos["huella"]["usuarios"], 8)
            self.assertEqual(datos["huella"]["condominios"],
                             ["Condominio Vista Verde", "Edificio Los Aromos"])
            self.assertEqual(datos["huella"]["suma_cobros"], {"s": 4989239, "f": 249462})
            self.assertEqual(datos["periodos"], [
                [2026, 9, "EMITIDO"], [2026, 10, "EMITIDO"],
                [2026, 11, "ABIERTO"], [2026, 10, "EMITIDO"],
            ])
            ruta = Path(temporal) / ".demo_cliente/demo.sqlite3"
            self.assertTrue(ruta.is_file())
            self.assertIn(str(ruta.resolve()), resultado.stdout)
            self.assertIn("ficticios", resultado.stdout)
            self.assertLess(resultado.stdout.index(str(ruta.resolve())),
                            resultado.stdout.index("Applying"))


class DatosDemoClienteTest(TestCase):
    def test_cookies_demo_no_sobrescriben_entorno_habitual(self):
        with override_settings(
            SESSION_COOKIE_NAME=getattr(settings_demo, "SESSION_COOKIE_NAME", "sessionid"),
            CSRF_COOKIE_NAME=getattr(settings_demo, "CSRF_COOKIE_NAME", "csrftoken"),
        ):
            respuesta = self.client.get(reverse("cuentas:iniciar_sesion"))
            self.assertEqual(respuesta.status_code, 200)
            usuario = Usuario.objects.create_user(email="cuenta-ficticia@example.com")
            self.client.force_login(usuario)
            self.assertEqual(set(self.client.cookies),
                             {"condohub_demo_sessionid", "condohub_demo_csrftoken"})

    def test_fecha_referencia_opcional_conserva_carga_normal(self):
        with patch("apps.gastos.demo.date") as fecha:
            fecha.today.return_value = date(2025, 2, 15)
            call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(pruebas_core.huella_demo(), pruebas_core.CargarDemoTest.HUELLA)
        self.assertEqual(list(PeriodoGasto.objects.filter(
            condominio__nombre="Condominio Vista Verde").order_by("anio", "mes")
            .values_list("anio", "mes")), [(2024, 12), (2025, 1), (2025, 2)])

    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16))
    def test_saldo_demo_coincide_movimientos(self):
        with patch("apps.gastos.demo.date") as fecha:
            fecha.today.return_value = date(2025, 2, 15)
            call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(pruebas_core.huella_demo(), pruebas_core.CargarDemoTest.HUELLA)
        for nombre, saldo, meses, apertura in [
            ("Condominio Vista Verde", 1140537, [9, 10, 11], 1000000),
            ("Edificio Los Aromos", 533925, [10], 500000),
        ]:
            with self.subTest(condominio=nombre):
                condominio = Condominio.objects.get(nombre=nombre)
                periodos = PeriodoGasto.objects.filter(condominio=condominio).order_by("mes")
                self.assertEqual(list(periodos.values_list("anio", "mes")),
                                 [(2026, mes) for mes in meses])
                inicial = MovimientoFondo.objects.get(condominio=condominio, tipo="INICIAL")
                self.assertEqual(inicial.monto, apertura)
                self.assertLess(inicial.fecha, date(2026, 9, 1))
                self.assertEqual(saldo_fondo(condominio), saldo)
                self.assertEqual(sum(m.monto for m in movimientos_fondo(condominio)), saldo)
                for periodo in periodos.filter(estado="EMITIDO"):
                    ingreso = MovimientoFondo.objects.get(periodo=periodo, tipo="INGRESO")
                    self.assertEqual(ingreso.monto,
                        periodo.detalles.aggregate(s=Sum("monto_fondo_reserva"))["s"])
                    self.assertEqual(saldo_fondo(condominio, periodo), sum(
                        m.monto for m in movimientos_fondo(condominio)
                        if m.fecha <= ingreso.fecha))
        egreso = MovimientoFondo.objects.get(tipo="EGRESO")
        self.assertEqual((egreso.monto, egreso.fecha), (-75000, date(2026, 10, 31)))
        self.assertTrue(egreso.acuerdo)
        self.assertIn("ficticia", egreso.descripcion)
