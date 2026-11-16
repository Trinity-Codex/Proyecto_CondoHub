"""Proveedores ficticios de Los Aromos en la demo del cliente (Issue #98)."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.gastos.models import Egreso
from apps.proveedores.models import Proveedor

# Los de Vista Verde no cambian con el modo cliente: 3 activos y 1 inactivo.
VISTA_VERDE = {"Ascensores Sur SpA", "Aseo Limpio Ltda.", "Seguridad Andes S.A.", "Jardines del Valle"}


def _de(condominio):
    return Proveedor.objects.filter(condominio__nombre=condominio)


class ProveedoresDemoTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16))
    def test_con_fecha_los_aromos_tiene_dos_activos(self):
        call_command("cargar_demo", stdout=StringIO())
        aromos = _de("Edificio Los Aromos")
        self.assertEqual(aromos.filter(activo=True).count(), 2)
        self.assertEqual(aromos.count(), 2)
        for proveedor in aromos:  # full_clean valida el RUT con su dígito verificador
            proveedor.full_clean()
        self.assertFalse(Egreso.objects.filter(proveedor__in=aromos).exists())
        vista_verde = _de("Condominio Vista Verde")
        self.assertEqual({p.razon_social for p in vista_verde}, VISTA_VERDE)
        self.assertEqual(vista_verde.filter(activo=True).count(), 3)

    def test_sin_fecha_los_aromos_no_tiene_proveedores(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(_de("Edificio Los Aromos").count(), 0)
        vista_verde = _de("Condominio Vista Verde")
        self.assertEqual({p.razon_social for p in vista_verde}, VISTA_VERDE)
        self.assertEqual(vista_verde.filter(activo=True).count(), 3)
