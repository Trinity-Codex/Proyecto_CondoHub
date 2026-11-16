"""Incidentes ficticios de la demo del cliente (Issue #98)."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.incidentes.models import Incidente


class IncidentesDemoTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16))
    def test_tres_estados_incidente_solo_modo_cliente(self):
        call_command("cargar_demo", stdout=StringIO())
        estados = sorted(Incidente.objects.values_list("estado", flat=True))
        self.assertEqual(estados, ["EN_PROCESO", "RECIBIDO", "RESUELTO"])
        resuelto = Incidente.objects.get(estado=Incidente.Estado.RESUELTO)
        self.assertEqual(resuelto.condominio.nombre, "Condominio Vista Verde")
        self.assertTrue(resuelto.respuesta)  # el residente ve cómo se resolvió

    def test_sin_fecha_no_hay_resuelto(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertFalse(Incidente.objects.filter(estado=Incidente.Estado.RESUELTO).exists())
        self.assertEqual(Incidente.objects.count(), 2)
