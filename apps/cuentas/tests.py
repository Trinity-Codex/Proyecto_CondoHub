"""Pruebas de cuentas: RUT, creación de usuarios e inicio de sesión con correo."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.pruebas import CLAVE, crear_usuario

from .models import Usuario
from .validadores import calcular_dv, validar_rut


class RutTest(SimpleTestCase):
    def test_ruts_validos(self):
        for rut in ["12.345.678-5", "12345678-5", "11111111-1", "7.654.321-6", "15.975.346-8"]:
            validar_rut(rut)  # no debe lanzar error

    def test_digito_verificador_k(self):
        self.assertEqual(calcular_dv("10000013"), "K")
        validar_rut("10.000.013-k")  # la k minúscula también vale

    def test_ruts_invalidos(self):
        for rut in ["12.345.678-9", "123", "12345678", "abc-1"]:
            with self.assertRaises(ValidationError, msg=rut):
                validar_rut(rut)


class UsuarioTest(TestCase):
    def test_crear_usuario_con_correo(self):
        usuario = crear_usuario("persona@prueba.cl", rut="12.345.678-5")
        self.assertTrue(usuario.check_password(CLAVE))
        self.assertEqual(usuario.rut, "12345678-5")  # se guarda normalizado
        self.assertFalse(usuario.is_superuser)

    def test_crear_superusuario(self):
        usuario = Usuario.objects.create_superuser("root@prueba.cl", "clave")
        self.assertTrue(usuario.is_superuser and usuario.is_staff)

    def test_iniciar_sesion_con_correo(self):
        crear_usuario("persona@prueba.cl")
        respuesta = self.client.post(
            reverse("cuentas:iniciar_sesion"), {"username": "persona@prueba.cl", "password": CLAVE}
        )
        self.assertRedirects(respuesta, reverse("core:inicio"), fetch_redirect_response=False)

    def test_clave_incorrecta(self):
        crear_usuario("persona@prueba.cl")
        respuesta = self.client.post(
            reverse("cuentas:iniciar_sesion"), {"username": "persona@prueba.cl", "password": "mala"}
        )
        self.assertEqual(respuesta.status_code, 200)  # vuelve a mostrar el formulario
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)
