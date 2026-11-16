"""Pagos ficticios de Los Aromos en la demo del cliente (Issue #98)."""
from datetime import date
from importlib import import_module
from io import StringIO

from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase, override_settings

from apps.core.management.commands.cargar_demo import APPS_DEMO
from apps.gastos.fondo import movimientos_fondo, saldo_fondo
from apps.gastos.models import DetalleGastoComun
from apps.pagos.models import Pago

REFERENCIA = date(2026, 11, 16)


def _cobros_aromos():
    return DetalleGastoComun.objects.filter(periodo__condominio__nombre="Edificio Los Aromos")


class PagosDemoLosAromosTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=REFERENCIA)
    def test_los_aromos_tiene_pago_sin_duplicar_fondo(self):
        call_command("cargar_demo", stdout=StringIO())
        cobros = _cobros_aromos()
        # 2 cobros pagados, 1 con abono parcial y 1 pendiente sin pagos.
        pagados = cobros.filter(estado=DetalleGastoComun.Estado.PAGADO)
        pendientes = cobros.filter(estado=DetalleGastoComun.Estado.PENDIENTE)
        parciales = [c for c in pendientes if 0 < (c.pagos.aggregate(s=Sum("monto"))["s"] or 0) < c.total]
        sin_pagos = pendientes.filter(pagos__isnull=True)
        self.assertEqual((pagados.count(), len(parciales), sin_pagos.count()), (2, 1, 1))
        for cobro in pagados:
            self.assertEqual(cobro.pagos.aggregate(s=Sum("monto"))["s"], cobro.total)
        # Recaudación y pertenencia: todos los pagos de la demo en Los Aromos son de sus cobros.
        pagos = Pago.objects.filter(detalle__in=cobros)
        self.assertGreater(pagos.aggregate(s=Sum("monto"))["s"], 0)
        self.assertEqual(Pago.objects.filter(detalle__periodo__condominio__nombre="Edificio Los Aromos").count(), pagos.count())
        for pago in pagos:
            self.assertEqual(pago.condominio.nombre, "Edificio Los Aromos")
            self.assertLessEqual(pago.fecha, REFERENCIA)

    def test_pagar_no_toca_el_fondo_de_los_aromos(self):
        # Se cargan las apps en orden hasta gastos, se anota el libro del fondo y luego se cargan los pagos.
        datos = {"fecha_referencia_demo": REFERENCIA}
        for app in APPS_DEMO[:APPS_DEMO.index("pagos")]:
            import_module(f"apps.{app}.demo").cargar(datos)
        aromos = datos["los_aromos"]
        antes = list(movimientos_fondo(aromos).values_list("pk", "tipo", "monto"))
        saldo = saldo_fondo(aromos)
        import_module("apps.pagos.demo").cargar(datos)
        self.assertEqual(list(movimientos_fondo(aromos).values_list("pk", "tipo", "monto")), antes)
        self.assertEqual(saldo_fondo(aromos), saldo)
        self.assertTrue(Pago.objects.filter(detalle__periodo=datos["periodos"]["los_aromos"]).exists())

    def test_sin_fecha_los_aromos_no_tiene_pagos(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertFalse(Pago.objects.filter(detalle__in=_cobros_aromos()).exists())
