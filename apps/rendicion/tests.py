"""Pruebas de rendicion: página provisional y permisos por rol (contrato C0, #62)."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario


class PaginaProvisionalTest(TestCase):
    """Entran el administrador y el comité (200); los demás roles reciben 403 y sin sesión se pide iniciarla."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("rendicion:inicio")

    def test_quien_puede_entrar(self):
        esperados = [
            (self.e.administrador, 200),
            (self.e.comite, 200),
            (self.e.conserje, 403),
            (self.e.residente, 403),
        ]
        for usuario, esperado in esperados:
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, esperado)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(
            respuesta, reverse("cuentas:iniciar_sesion") + "?next=" + self.url, fetch_redirect_response=False
        )

    def test_el_menu_tiene_el_enlace(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("core:inicio")), self.url)
