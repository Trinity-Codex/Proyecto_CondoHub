"""Pruebas de cuentas: RUT, usuarios, inicio de sesión, recuperar contraseña y alta (Issue #11)."""
import re
from datetime import timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.condominios.models import Membresia
from apps.core.pruebas import CLAVE, crear_escenario, crear_usuario

from . import limite_intentos
from .models import IntentoFallido, Usuario
from .validadores import calcular_dv, normalizar_rut, validar_rut


class RutTest(SimpleTestCase):
    def test_ruts_validos(self):
        for rut in ["12.345.678-5", "12345678-5", "11111111-1", "7.654.321-6", "15.975.346-8"]:
            validar_rut(rut)  # no debe lanzar error
            numero, dv = normalizar_rut(rut).split("-")
            self.assertEqual(calcular_dv(numero), dv, msg=rut)

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

    def test_no_repite_el_rut_de_otra_persona(self):
        # Caso encontrado por Winderson en la revisión: se podía crear otra cuenta con el RUT de la administradora.
        self.e.administrador.rut = "12.345.678-5"
        self.e.administrador.save()
        respuesta = self.alta(rut="12345678-5")  # mismo RUT escrito sin puntos
        self.assertEqual(respuesta.context["form"].errors["rut"], ["Ya existe otra cuenta con ese RUT."])
        self.assertFalse(Usuario.objects.filter(email="nuevo@prueba.cl").exists())

    def test_correo_existente_no_valida_el_rut_del_formulario(self):
        # Si la cuenta ya existe, sus datos no se tocan: el RUT escrito no importa.
        self.e.administrador.rut = "12.345.678-5"
        self.e.administrador.save()
        respuesta = self.alta(email="ajeno@prueba.cl", rut="12.345.678-5")
        self.assertRedirects(respuesta, reverse("cuentas:usuarios"))
        self.assertTrue(self.tiene_rol(self.e.residente_ajeno, self.e.condominio))

    def test_validar_rut_disponible_ignora_el_propio(self):
        # Para el perfil (#12): al editar su cuenta, la persona puede conservar su propio RUT.
        from .forms import validar_rut_disponible

        self.e.administrador.rut = "12.345.678-5"
        self.e.administrador.save()
        self.assertEqual(validar_rut_disponible("12.345.678-5", usuario=self.e.administrador), "12345678-5")
        with self.assertRaises(ValidationError):
            validar_rut_disponible("12.345.678-5", usuario=self.e.comite)

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


class PerfilTest(TestCase):
    """Issue #12: cada persona edita sus datos y cambia su contraseña."""

    def setUp(self):
        self.e = crear_escenario()
        self.usuario = self.e.residente
        self.client.force_login(self.usuario)

    def guardar(self, **campos):
        datos = {"first_name": "Valentina", "last_name": "Soto", "rut": "15.975.346-8", "telefono": "+56 9 1234 5678", **campos}
        return self.client.post(reverse("cuentas:perfil"), datos)

    def test_pide_iniciar_sesion(self):
        self.client.logout()
        respuesta = self.client.get(reverse("cuentas:perfil"))
        self.assertRedirects(respuesta, f"{reverse('cuentas:iniciar_sesion')}?next={reverse('cuentas:perfil')}")

    def test_el_menu_enlaza_a_mi_perfil(self):
        self.assertContains(self.client.get(reverse("core:inicio")), reverse("cuentas:perfil"))

    def test_actualiza_sus_datos(self):
        respuesta = self.guardar()
        self.assertRedirects(respuesta, reverse("cuentas:perfil"))
        self.usuario.refresh_from_db()
        self.assertEqual(
            (self.usuario.first_name, self.usuario.last_name, self.usuario.rut, self.usuario.telefono),
            ("Valentina", "Soto", "15975346-8", "+56 9 1234 5678"),
        )

    def test_el_correo_no_se_puede_cambiar(self):
        self.assertNotIn("email", self.client.get(reverse("cuentas:perfil")).context["form"].fields)
        self.guardar(email="otro@prueba.cl")  # aunque alguien lo envíe a mano, se ignora
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "residente@prueba.cl")

    def test_rut_invalido(self):
        respuesta = self.guardar(rut="15.975.346-1")
        self.assertIn("rut", respuesta.context["form"].errors)

    def test_rut_de_otra_persona(self):
        self.e.administrador.rut = "12.345.678-5"
        self.e.administrador.save()
        respuesta = self.guardar(rut="12345678-5")
        self.assertEqual(respuesta.context["form"].errors["rut"], ["Ya existe otra cuenta con ese RUT."])

    def test_conserva_su_propio_rut(self):
        self.guardar()
        respuesta = self.guardar(first_name="Vale")  # vuelve a guardar con el mismo RUT
        self.assertRedirects(respuesta, reverse("cuentas:perfil"))

    def test_telefono_invalido(self):
        respuesta = self.guardar(telefono="llámame")
        self.assertIn("telefono", respuesta.context["form"].errors)

    def test_solo_edita_su_propia_cuenta(self):
        self.guardar(first_name="Cambiado")
        self.e.administrador.refresh_from_db()
        self.assertNotEqual(self.e.administrador.first_name, "Cambiado")


class CambiarClaveTest(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("persona@prueba.cl")
        self.client.force_login(self.usuario)
        self.nueva = "Clave-nueva-segura-2026"

    def cambiar(self, actual=CLAVE):
        datos = {"old_password": actual, "new_password1": self.nueva, "new_password2": self.nueva}
        return self.client.post(reverse("cuentas:cambiar_clave"), datos)

    def test_cambia_la_clave_y_sigue_con_la_sesion_abierta(self):
        respuesta = self.cambiar()
        self.assertRedirects(respuesta, reverse("cuentas:perfil"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(self.nueva))
        self.assertTrue(self.client.get(reverse("cuentas:perfil")).wsgi_request.user.is_authenticated)

    def test_pide_la_clave_actual(self):
        respuesta = self.cambiar(actual="no-es-esta")
        self.assertIn("old_password", respuesta.context["form"].errors)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(CLAVE))

    def test_pide_iniciar_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("cuentas:cambiar_clave")).status_code, 302)


def envejecer_intentos(minutos=16):
    """Simula que pasó el tiempo: mueve al pasado los intentos guardados."""
    IntentoFallido.objects.update(creado=timezone.now() - timedelta(minutes=minutos))


class LimiteIntentosReglasTest(TestCase):
    """Issue #52: las reglas, sin pasar por las páginas."""

    def fallar(self, correo="a@prueba.cl", direccion="10.0.0.1", veces=5):
        for _ in range(veces):
            limite_intentos.registrar_fallo(correo, direccion)

    def test_cuatro_fallos_no_bloquean(self):
        self.fallar(veces=4)
        self.assertFalse(limite_intentos.esta_bloqueado("a@prueba.cl", "10.0.0.1"))

    def test_bloquea_el_correo_aunque_cambie_la_direccion(self):
        for numero in range(5):
            limite_intentos.registrar_fallo("a@prueba.cl", f"10.0.0.{numero}")
        self.assertTrue(limite_intentos.esta_bloqueado("a@prueba.cl", "10.9.9.9"))

    def test_bloquea_la_direccion_aunque_cambie_el_correo(self):
        for numero in range(5):
            limite_intentos.registrar_fallo(f"a{numero}@prueba.cl", "10.0.0.1")
        self.assertTrue(limite_intentos.esta_bloqueado("otro@prueba.cl", "10.0.0.1"))
        self.assertFalse(limite_intentos.esta_bloqueado("otro@prueba.cl", "10.0.0.2"))

    def test_sin_direccion_no_se_junta_a_personas_distintas(self):
        for numero in range(5):
            limite_intentos.registrar_fallo(f"a{numero}@prueba.cl", "")
        self.assertFalse(limite_intentos.esta_bloqueado("otro@prueba.cl", ""))

    def test_el_correo_se_normaliza(self):
        self.assertEqual(limite_intentos.normalizar_correo("  Ana@Prueba.CL "), "ana@prueba.cl")
        self.assertEqual(limite_intentos.normalizar_correo(None), "")

    def test_el_bloqueo_termina_cuando_los_intentos_salen_de_la_ventana(self):
        self.fallar()
        envejecer_intentos(minutos=14)
        self.assertTrue(limite_intentos.esta_bloqueado("a@prueba.cl", "10.0.0.1"))
        envejecer_intentos(minutos=16)
        self.assertFalse(limite_intentos.esta_bloqueado("a@prueba.cl", "10.0.0.1"))

    def test_los_intentos_antiguos_se_eliminan(self):
        self.fallar(veces=3)
        envejecer_intentos()
        limite_intentos.registrar_fallo("b@prueba.cl", "10.0.0.2")
        self.assertEqual(list(IntentoFallido.objects.values_list("correo", flat=True)), ["b@prueba.cl"])

    def test_un_ingreso_correcto_tambien_elimina_los_antiguos(self):
        self.fallar(veces=3)
        envejecer_intentos()
        limite_intentos.limpiar_correo("otra.persona@prueba.cl")
        self.assertFalse(IntentoFallido.objects.exists())


class DireccionClienteTest(SimpleTestCase):
    def peticion(self, **meta):
        return RequestFactory().post("/", REMOTE_ADDR="10.0.0.1", **meta)

    def test_sin_configuracion_ignora_una_cabecera_falsificada(self):
        peticion = self.peticion(HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(limite_intentos.direccion_cliente(peticion), "10.0.0.1")

    @override_settings(CUENTAS_PROXIES_CONFIABLES=1)
    def test_con_un_proxy_toma_lo_que_agrego_el_proxy(self):
        # El visitante puede inventar la primera parte; la última la escribe nuestro proxy.
        peticion = self.peticion(HTTP_X_FORWARDED_FOR="1.2.3.4, 200.1.1.1")
        self.assertEqual(limite_intentos.direccion_cliente(peticion), "200.1.1.1")

    @override_settings(CUENTAS_PROXIES_CONFIABLES="1")
    def test_el_ajuste_puede_venir_como_texto_de_una_variable_de_entorno(self):
        peticion = self.peticion(HTTP_X_FORWARDED_FOR="1.2.3.4, 200.1.1.1")
        self.assertEqual(limite_intentos.direccion_cliente(peticion), "200.1.1.1")

    @override_settings(CUENTAS_PROXIES_CONFIABLES=2)
    def test_con_dos_proxies_cuenta_desde_la_derecha(self):
        peticion = self.peticion(HTTP_X_FORWARDED_FOR="1.2.3.4, 200.1.1.1, 10.0.0.9")
        self.assertEqual(limite_intentos.direccion_cliente(peticion), "200.1.1.1")

    @override_settings(CUENTAS_PROXIES_CONFIABLES=1)
    def test_con_proxy_y_sin_cabecera_usa_remote_addr(self):
        self.assertEqual(limite_intentos.direccion_cliente(self.peticion()), "10.0.0.1")

    def test_sin_remote_addr_no_falla(self):
        peticion = self.peticion()
        del peticion.META["REMOTE_ADDR"]
        self.assertEqual(limite_intentos.direccion_cliente(peticion), "")

    def test_sin_peticion_no_falla(self):
        self.assertEqual(limite_intentos.direccion_cliente(None), "")


class LimiteIntentosSitioTest(TestCase):
    """Issue #52: el inicio de sesión del sitio."""

    def setUp(self):
        self.usuario = crear_usuario("persona@prueba.cl")

    def entrar(self, correo="persona@prueba.cl", clave="mala", **extra):
        return self.client.post(reverse("cuentas:iniciar_sesion"), {"username": correo, "password": clave}, **extra)

    def fallar(self, correo="persona@prueba.cl", veces=5):
        for _ in range(veces):
            respuesta = self.entrar(correo)
        return respuesta

    def errores(self, respuesta):
        return respuesta.context["form"].non_field_errors()

    def test_antes_del_limite_muestra_el_error_normal(self):
        self.assertNotIn(limite_intentos.MENSAJE_BLOQUEO, self.errores(self.fallar(veces=4)))

    def test_el_quinto_fallo_bloquea_y_dice_como_recuperar_la_clave(self):
        respuesta = self.fallar()
        self.assertEqual(self.errores(respuesta), [limite_intentos.MENSAJE_BLOQUEO])
        self.assertContains(respuesta, "Olvidaste tu contraseña")
        self.assertContains(respuesta, reverse("cuentas:recuperar_clave"))

    def test_la_clave_correcta_no_entra_durante_el_bloqueo(self):
        self.fallar()
        respuesta = self.entrar(clave=CLAVE)
        self.assertEqual(self.errores(respuesta), [limite_intentos.MENSAJE_BLOQUEO])
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cambiar_mayusculas_no_evita_el_limite(self):
        correos = ["persona@prueba.cl", "PERSONA@prueba.cl", "Persona@Prueba.cl", "persona@PRUEBA.cl", "PERSONA@PRUEBA.CL"]
        for numero, correo in enumerate(correos):
            respuesta = self.entrar(correo, REMOTE_ADDR=f"10.0.1.{numero}")  # direcciones distintas: solo cuenta el correo
        self.assertEqual(self.errores(respuesta), [limite_intentos.MENSAJE_BLOQUEO])

    def test_el_mensaje_no_revela_si_el_correo_existe(self):
        for intento in range(1, 6):
            with self.subTest(intento=intento):
                existe = self.entrar("persona@prueba.cl", REMOTE_ADDR="10.0.0.1")
                no_existe = self.entrar("nadie@prueba.cl", REMOTE_ADDR="10.0.0.2")
                self.assertEqual(self.errores(existe), self.errores(no_existe))
        self.assertEqual(self.errores(existe), [limite_intentos.MENSAJE_BLOQUEO])

    def test_el_bloqueo_termina_solo_y_la_persona_entra(self):
        self.fallar()
        envejecer_intentos()
        respuesta = self.entrar(clave=CLAVE)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_los_intentos_durante_el_bloqueo_no_lo_alargan(self):
        self.fallar()
        self.fallar(veces=3)
        self.assertEqual(IntentoFallido.objects.count(), 5)

    def test_ingresar_bien_reinicia_el_contador(self):
        self.fallar(veces=4)
        self.assertEqual(self.entrar(clave=CLAVE).status_code, 302)
        self.assertFalse(IntentoFallido.objects.exists())

    def test_ingresar_con_otra_cuenta_no_borra_los_intentos_contra_esta(self):
        crear_usuario("atacante@prueba.cl")
        self.fallar(veces=4)
        self.assertEqual(self.entrar("atacante@prueba.cl", CLAVE).status_code, 302)
        self.client.logout()
        self.assertEqual(IntentoFallido.objects.filter(correo="persona@prueba.cl").count(), 4)
        self.assertEqual(self.errores(self.entrar()), [limite_intentos.MENSAJE_BLOQUEO])

    def test_un_formulario_incompleto_no_cuenta_como_intento(self):
        self.client.post(reverse("cuentas:iniciar_sesion"), {"username": "persona@prueba.cl", "password": ""})
        self.client.post(reverse("cuentas:iniciar_sesion"), {"username": "no-es-correo", "password": "x"})
        self.assertFalse(IntentoFallido.objects.exists())

    def test_recuperar_la_clave_desbloquea_de_inmediato(self):
        self.fallar()
        self.client.post(reverse("cuentas:recuperar_clave"), {"email": "persona@prueba.cl"})
        nueva = "Clave-nueva-segura-2026"
        definir_clave(self.client, enlace_del_correo(mail.outbox[0]), nueva)
        self.assertEqual(self.entrar(clave=nueva).status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_recuperar_la_clave_no_libera_una_direccion_bloqueada_por_otros_correos(self):
        for numero in range(5):
            self.entrar(f"otro{numero}@prueba.cl", REMOTE_ADDR="10.0.0.1")
        self.client.post(reverse("cuentas:recuperar_clave"), {"email": "persona@prueba.cl"})
        nueva = "Clave-nueva-segura-2026"
        definir_clave(self.client, enlace_del_correo(mail.outbox[0]), nueva)
        # Desde esa dirección espera; desde otra, entra de inmediato.
        self.assertEqual(self.errores(self.entrar(clave=nueva, REMOTE_ADDR="10.0.0.1")), [limite_intentos.MENSAJE_BLOQUEO])
        self.assertEqual(self.entrar(clave=nueva, REMOTE_ADDR="10.0.0.2").status_code, 302)


class LimiteIntentosAdminTest(TestCase):
    """Issue #52: /admin/ también comprueba claves, así que no puede ser una puerta sin límite."""

    def setUp(self):
        self.root = Usuario.objects.create_superuser("root@prueba.cl", CLAVE)

    def entrar(self, clave="mala"):
        return self.client.post(reverse("admin:login"), {"username": "root@prueba.cl", "password": clave, "next": "/admin/"})

    def test_cinco_fallos_bloquean(self):
        for _ in range(5):
            respuesta = self.entrar()
        self.assertContains(respuesta, limite_intentos.MENSAJE_BLOQUEO)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.entrar(CLAVE).status_code, 200)  # ni con la clave correcta
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_el_superusuario_entra_sin_bloqueo(self):
        self.assertEqual(self.entrar(CLAVE).status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_los_fallos_en_admin_cuentan_para_el_sitio(self):
        for _ in range(5):
            self.entrar()
        respuesta = self.client.post(reverse("cuentas:iniciar_sesion"), {"username": "root@prueba.cl", "password": CLAVE})
        self.assertEqual(respuesta.context["form"].non_field_errors(), [limite_intentos.MENSAJE_BLOQUEO])

    def test_una_cuenta_sin_permiso_de_admin_cuenta_como_fallo_y_no_entra(self):
        crear_usuario("persona@prueba.cl")
        self.client.post(reverse("admin:login"), {"username": "persona@prueba.cl", "password": CLAVE, "next": "/admin/"})
        self.assertEqual(IntentoFallido.objects.filter(correo="persona@prueba.cl").count(), 1)
        self.assertNotIn("_auth_user_id", self.client.session)
