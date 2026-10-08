"""Pruebas de cuentas: RUT, usuarios, inicio de sesión, recuperar contraseña y alta (Issue #11)."""
import re

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.condominios.models import Membresia
from apps.core.pruebas import CLAVE, crear_escenario, crear_usuario

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


def enlace_del_correo(correo):
    """Extrae la ruta /cuentas/nueva-clave/... del texto de un correo."""
    return re.search(r"https?://[^/]+(/cuentas/nueva-clave/\S+)", correo.body).group(1)


def definir_clave(cliente, enlace, clave):
    """Abre el enlace del correo y guarda la clave. Devuelve la respuesta del POST."""
    # Al abrir el enlace, Django redirige a una URL ".../set-password/" (así el token no queda en el historial).
    formulario = cliente.get(enlace, follow=True)
    assert formulario.context["validlink"], "El enlace del correo debería ser válido"
    return cliente.post(formulario.request["PATH_INFO"], {"new_password1": clave, "new_password2": clave})


class RecuperarClaveTest(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("persona@prueba.cl")

    def test_en_desarrollo_los_correos_van_a_la_consola(self):
        # Durante las pruebas Django cambia el backend por uno en memoria (mail.outbox);
        # aquí se revisa el valor configurado en settings.py.
        from config import settings as configuracion

        self.assertEqual(configuracion.EMAIL_BACKEND, "django.core.mail.backends.console.EmailBackend")

    def test_el_inicio_de_sesion_enlaza_a_recuperar_clave(self):
        self.assertContains(self.client.get(reverse("cuentas:iniciar_sesion")), reverse("cuentas:recuperar_clave"))

    def test_flujo_completo(self):
        respuesta = self.client.post(reverse("cuentas:recuperar_clave"), {"email": "persona@prueba.cl"})
        self.assertRedirects(respuesta, reverse("cuentas:recuperar_clave_enviado"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["persona@prueba.cl"])

        nueva = "Otra-clave-segura-2026"
        respuesta = definir_clave(self.client, enlace_del_correo(mail.outbox[0]), nueva)
        self.assertRedirects(respuesta, reverse("cuentas:nueva_clave_lista"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(nueva))

    def test_correo_desconocido_no_revela_nada(self):
        respuesta = self.client.post(reverse("cuentas:recuperar_clave"), {"email": "nadie@prueba.cl"})
        self.assertRedirects(respuesta, reverse("cuentas:recuperar_clave_enviado"))
        self.assertEqual(len(mail.outbox), 0)

    def test_enlace_invalido(self):
        respuesta = self.client.get(reverse("cuentas:nueva_clave", args=["xx", "token-falso"]))
        self.assertFalse(respuesta.context["validlink"])


class AltaUsuarioTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def alta(self, **campos):
        datos = {
            "email": "nuevo@prueba.cl",
            "first_name": "Ana",
            "last_name": "Pérez",
            "rut": "12.345.678-5",
            "rol": Membresia.Rol.CONSERJE,
            **campos,
        }
        return self.client.post(reverse("cuentas:usuario_nuevo"), datos)

    def tiene_rol(self, usuario, condominio, rol=Membresia.Rol.CONSERJE):
        return Membresia.objects.filter(usuario=usuario, condominio=condominio, rol=rol, activo=True).exists()

    def test_crea_usuario_con_rol_en_el_condominio_activo(self):
        respuesta = self.alta()
        self.assertRedirects(respuesta, reverse("cuentas:usuarios"))
        usuario = Usuario.objects.get(email="nuevo@prueba.cl")
        self.assertEqual((usuario.first_name, usuario.rut), ("Ana", "12345678-5"))
        self.assertTrue(self.tiene_rol(usuario, self.e.condominio))
        self.assertFalse(Membresia.objects.filter(usuario=usuario, condominio=self.e.ajeno).exists())

    def test_envia_invitacion_y_la_persona_define_su_clave(self):
        self.alta()
        self.assertEqual(len(mail.outbox), 1)
        invitacion = mail.outbox[0]
        self.assertEqual(invitacion.to, ["nuevo@prueba.cl"])
        self.assertIn("Prueba", invitacion.body)  # nombre del condominio
        self.assertIn("Conserje", invitacion.body)

        self.client.logout()
        clave = "Mi-clave-nueva-2026"
        definir_clave(self.client, enlace_del_correo(invitacion), clave)
        self.assertTrue(self.client.login(username="nuevo@prueba.cl", password=clave))

    def test_correo_existente_solo_agrega_el_rol(self):
        # El residente del otro condominio pasa a ser también conserje de este.
        respuesta = self.alta(email="AJENO@prueba.cl", first_name="Otro nombre")
        self.assertRedirects(respuesta, reverse("cuentas:usuarios"))
        self.assertEqual(Usuario.objects.filter(email__iexact="ajeno@prueba.cl").count(), 1)
        self.e.residente_ajeno.refresh_from_db()
        self.assertNotEqual(self.e.residente_ajeno.first_name, "Otro nombre")  # no se tocan sus datos
        self.assertTrue(self.tiene_rol(self.e.residente_ajeno, self.e.condominio))
        self.assertEqual(len(mail.outbox), 0)  # ya tiene clave: no se envía invitación

    def test_no_repite_un_rol_que_ya_tiene(self):
        respuesta = self.alta(email="conserje@prueba.cl")
        self.assertIn("rol", respuesta.context["form"].errors)

    def test_reactiva_un_rol_dado_de_baja(self):
        Membresia.objects.filter(usuario=self.e.conserje).update(activo=False)
        self.alta(email="conserje@prueba.cl")
        self.assertTrue(self.tiene_rol(self.e.conserje, self.e.condominio))

    def test_rut_invalido(self):
        respuesta = self.alta(rut="12.345.678-9")
        self.assertIn("rut", respuesta.context["form"].errors)
        self.assertFalse(Usuario.objects.filter(email="nuevo@prueba.cl").exists())

    def test_solo_el_administrador(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.email):
                self.assertEqual(self.client.get(reverse("cuentas:usuario_nuevo")).status_code, 403)
                self.assertEqual(self.client.get(reverse("cuentas:usuarios")).status_code, 403)

    def test_un_administrador_no_asigna_roles_en_condominios_ajenos(self):
        # Aunque fuerce el condominio ajeno en su sesión, el middleware lo ignora
        # (no es miembro) y el rol queda en su propio condominio.
        sesion = self.client.session
        sesion["condominio_id"] = self.e.ajeno.pk
        sesion.save()
        self.alta()
        usuario = Usuario.objects.get(email="nuevo@prueba.cl")
        self.assertFalse(Membresia.objects.filter(usuario=usuario, condominio=self.e.ajeno).exists())
        self.assertTrue(self.tiene_rol(usuario, self.e.condominio))

    def test_lista_muestra_solo_usuarios_del_condominio(self):
        usuarios = list(self.client.get(reverse("cuentas:usuarios")).context["usuarios"])
        self.assertIn(self.e.residente, usuarios)
        self.assertNotIn(self.e.residente_ajeno, usuarios)
