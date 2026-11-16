"""Reservas ficticias de la demo del cliente (Issue #96)."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.reservas.models import Reserva

FECHA_DEMO = date(2026, 11, 16)


class ReservasDemoTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=FECHA_DEMO)
    def test_reservas_posteriores_16nov(self):
        call_command("cargar_demo", stdout=StringIO())
        base = max(FECHA_DEMO, date.today())
        nuevas = Reserva.objects.filter(estado=Reserva.Estado.CONFIRMADA, fecha__gt=base)
        self.assertGreaterEqual(nuevas.count(), 3)  # la de siempre + las dos de la demo
        # En espacios y unidades distintos, todas de Vista Verde y sin superponerse.
        demo = nuevas.exclude(espacio__nombre="Quincho")
        self.assertEqual(sorted(demo.values_list("espacio__nombre", flat=True)), ["Gimnasio", "Salón de eventos"])
        for r in nuevas:
            self.assertEqual(r.espacio.condominio.nombre, "Condominio Vista Verde")
            self.assertTrue(r.solicitante.residencias.filter(unidad=r.unidad, activo=True).exists())
            r.full_clean()  # sigue cumpliendo las reglas de reserva (horario, sin topes)

    def test_sin_fecha_solo_la_reserva_habitual(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(Reserva.objects.count(), 1)
