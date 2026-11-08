"""Pruebas de privacidad: el aviso es público y se enlaza desde el pie de página (contrato C0, #62)."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario


class AvisoPrivacidadTest(TestCase):
    def setUp(self):
        self.url = reverse("privacidad:aviso")

    def test_se_lee_sin_iniciar_sesion(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "<h1", count=1)
        self.assertContains(respuesta, "Aviso de privacidad")

    def test_todos_los_roles_lo_ven(self):
        e = crear_escenario()
        for usuario in (e.administrador, e.comite, e.conserje, e.residente):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_el_pie_de_pagina_tiene_el_enlace(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, f'href="{self.url}"')
