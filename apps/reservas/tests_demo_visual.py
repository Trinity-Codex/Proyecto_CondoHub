"""Pruebas de presentación de reservas para la demo (Issue #95): tarifas con el filtro pesos."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario


class TarifasConPesosTest(TestCase):
    """El listado y el detalle de espacios muestran la tarifa con puntos de miles o «Sin costo»."""

    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.residente)

    def ver(self, nombre_url, *args):
        respuesta = self.client.get(reverse(nombre_url, args=args))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def test_tarifa_reserva_con_pesos(self):
        self.e.quincho.tarifa = 15000
        self.e.quincho.save()
        for html in (self.ver("reservas:espacios"), self.ver("reservas:espacio_detalle", self.e.quincho.pk)):
            self.assertIn("$15.000 por reserva", html)
            self.assertNotIn("$15000", html)
        # Solo cambia cómo se muestra: el valor guardado sigue igual.
        self.e.quincho.refresh_from_db()
        self.assertEqual(self.e.quincho.tarifa, 15000)

    def test_espacio_sin_costo(self):
        self.assertEqual(self.e.quincho.tarifa, 0)
        for html in (self.ver("reservas:espacios"), self.ver("reservas:espacio_detalle", self.e.quincho.pk)):
            self.assertIn("Sin costo", html)
            self.assertNotIn("$0", html)
