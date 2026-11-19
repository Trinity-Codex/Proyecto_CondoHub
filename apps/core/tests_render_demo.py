"""Demo visual de solo lectura en Render (Issue #111): configuración y bloqueo de escrituras."""
import json
import os
import runpy
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from apps.comunicados.models import Comunicado
from apps.core.pruebas import CLAVE, crear_escenario, crear_usuario
from apps.cuentas.models import Usuario
from apps.notificaciones.models import Notificacion
from config.settings import MIDDLEWARE as MIDDLEWARE_NORMAL

MIDDLEWARE_DEMO = "apps.core.middleware_demo.SoloLecturaDemoMiddleware"
AVISO = "Demo de solo lectura · Datos ficticios"
BLOQUEO = "Acción no disponible en la demo"
# Clave de prueba generada aquí, sin valor real: solo cumple el largo que exige la configuración.
CLAVE_PRUEBA = "prueba-render-" + "abcdefghij" * 5
HOST = "condohub-demo.onrender.com"


def cliente_demo(**opciones):
    """Conserva el host y HTTPS de Render al probar su configuración real."""
    host = settings.ALLOWED_HOSTS[0]
    if settings.SECURE_PROXY_SSL_HEADER:
        opciones.update(HTTP_X_FORWARDED_PROTO="https", HTTP_ORIGIN=f"https://{host}")
    return Client(HTTP_HOST=host, **opciones)


def configuracion_render(**variables):
    """Ejecuta config/settings_render_demo.py con esas variables de entorno y devuelve sus valores."""
    entorno = {"DJANGO_SECRET_KEY": CLAVE_PRUEBA, "RENDER_EXTERNAL_HOSTNAME": HOST, **variables}
    with patch.dict(os.environ, entorno):
        return runpy.run_module("config.settings_render_demo")


def rutas_sin_parametros(patrones=None, prefijo=""):
    """Nombres de todas las rutas GET del proyecto que no piden parámetros (ej. «comunicados:lista»)."""
    patrones = get_resolver().url_patterns if patrones is None else patrones
    nombres = []
    for patron in patrones:
        if isinstance(patron, URLResolver):
            espacio = f"{prefijo}{patron.namespace}:" if patron.namespace else prefijo
            if not patron.pattern.regex.groups:
                nombres += rutas_sin_parametros(patron.url_patterns, espacio)
        elif isinstance(patron, URLPattern) and patron.name and not patron.pattern.regex.groups:
            nombres.append(prefijo + patron.name)
    return nombres


def foto_negocio():
    """Todas las filas de todos los modelos, salvo sesiones y last_login (la demo sí los escribe)."""
    foto = {}
    for modelo in apps.get_models():
        if modelo is Session:
            continue
        filas = list(modelo.objects.order_by("pk").values())
        if modelo is Usuario:
            for fila in filas:
                fila.pop("last_login")
        foto[modelo._meta.label] = filas
    return foto


class ConfiguracionRenderTest(TestCase):
    def test_valores_publicos_y_seguridad(self):
        c = configuracion_render()
        self.assertFalse(c["DEBUG"])
        self.assertEqual(c["ALLOWED_HOSTS"], [HOST])
        self.assertEqual(c["CSRF_TRUSTED_ORIGINS"], [f"https://{HOST}"])
        self.assertEqual(c["SITIO_URL"], f"https://{HOST}")
        self.assertTrue(c["SECURE_SSL_REDIRECT"] and c["SESSION_COOKIE_SECURE"] and c["CSRF_COOKIE_SECURE"])
        self.assertEqual(c["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(c["EMAIL_BACKEND"], "django.core.mail.backends.dummy.EmailBackend")
        # Misma SQLite aislada de la demo local: preparar_demo_cliente la valida antes de escribir.
        self.assertEqual(c["DATABASES"]["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(c["DATABASES"]["default"]["NAME"], settings.BASE_DIR / ".demo_cliente" / "demo.sqlite3")
        self.assertTrue(hasattr(c["DEMO_FECHA_REFERENCIA"], "year"))

    def test_middleware_conserva_permisos_y_bloquea_despues_de_csrf(self):
        orden = configuracion_render()["MIDDLEWARE"]
        self.assertEqual(orden[:2], ["django.middleware.security.SecurityMiddleware",
                                     "whitenoise.middleware.WhiteNoiseMiddleware"])
        self.assertEqual(orden[-1], MIDDLEWARE_DEMO)
        # Todos los middleware habituales (CSRF, sesión, condominio activo) siguen, en su orden.
        self.assertEqual([m for m in orden if m in MIDDLEWARE_NORMAL], MIDDLEWARE_NORMAL)
        self.assertNotIn(MIDDLEWARE_DEMO, MIDDLEWARE_NORMAL)

    def test_secreto_ausente_o_de_desarrollo_detiene_el_arranque(self):
        for clave in ["", "corta", "x" * 60, "django-insecure-condohub-solo-para-desarrollo" + "y" * 10]:
            with self.subTest(largo=len(clave)), self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_SECRET_KEY"):
                configuracion_render(DJANGO_SECRET_KEY=clave)

    def test_acepta_el_formato_corto_del_generador_de_render(self):
        clave_generada = token_urlsafe(32)
        self.assertEqual(configuracion_render(DJANGO_SECRET_KEY=clave_generada)["SECRET_KEY"], clave_generada)

    def test_host_invalido_detiene_el_arranque(self):
        for host in ["", "localhost", "*.onrender.com", ".onrender.com", "demo.onrender.com:8000",
                     "demo.onrender.com/ruta", "https://demo.onrender.com", "Demo.onrender.com", "demo..com"]:
            with self.subTest(host=host), self.assertRaisesMessage(ImproperlyConfigured, "RENDER_EXTERNAL_HOSTNAME"):
                configuracion_render(RENDER_EXTERNAL_HOSTNAME=host)

    def test_preparacion_con_almacenamiento_vacio_no_duplica(self):
        # Proceso aparte con la configuración de Render real; BASE_DIR temporal para no tocar el repo.
        codigo = textwrap.dedent('''
            import json, sys
            from pathlib import Path
            import django
            from django.conf import settings
            settings.BASE_DIR = Path(sys.argv[1])
            settings.DATABASES["default"]["NAME"] = settings.BASE_DIR / ".demo_cliente/demo.sqlite3"
            settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
            django.setup()
            from django.apps import apps
            from django.core.management import call_command
            foto = lambda: {m._meta.label: list(m.objects.order_by("pk").values()) for m in apps.get_models()}
            call_command("preparar_demo_cliente")
            antes = foto()
            call_command("preparar_demo_cliente")
            print("RESULTADO=" + json.dumps({"sin_cambios": antes == foto(),
                                             "usuarios": len(antes["cuentas.Usuario"])}))
        ''')
        with tempfile.TemporaryDirectory() as temporal:
            entorno = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings_render_demo",
                       "DJANGO_SECRET_KEY": CLAVE_PRUEBA, "RENDER_EXTERNAL_HOSTNAME": HOST,
                       "PYTHONIOENCODING": "utf-8"}
            resultado = subprocess.run([sys.executable, "-c", codigo, temporal], cwd=settings.BASE_DIR,
                                       env=entorno, capture_output=True, text=True, encoding="utf-8", timeout=180)
            self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
            datos = json.loads(resultado.stdout.split("RESULTADO=")[-1])
            self.assertTrue(datos["sin_cambios"])
            self.assertEqual(datos["usuarios"], 8)
            self.assertTrue((Path(temporal) / ".demo_cliente/demo.sqlite3").is_file())


@override_settings(MIDDLEWARE=[m for m in settings.MIDDLEWARE if m != MIDDLEWARE_DEMO] + [MIDDLEWARE_DEMO])
class SoloLecturaDemoTest(TestCase):
    def setUp(self):
        self.client = cliente_demo()
        self.e = crear_escenario()
        self.comunicado = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Aviso", contenido="Texto")
        self.notificacion = Notificacion.objects.create(
            usuario=self.e.residente, condominio=self.e.condominio, titulo="Aviso", mensaje="x",
            url=self.comunicado.get_absolute_url())

    def assertBloqueada(self, respuesta):
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, BLOQUEO, status_code=403)
        self.assertContains(respuesta, AVISO, status_code=403)

    def test_navegacion_por_rol_con_aviso(self):
        paginas = {
            self.e.administrador: ["core:inicio", "comunicados:lista", "condominios:unidades", "cuentas:usuarios",
                                   "gastos:periodos", "pagos:cobranza", "proveedores:lista", "notificaciones:lista"],
            self.e.residente: ["core:inicio", "comunicados:lista", "reservas:espacios", "incidentes:lista",
                               "pagos:estado_cuenta", "notificaciones:lista", "cuentas:perfil"],
        }
        for usuario, rutas in paginas.items():
            self.client.force_login(usuario)
            for ruta in rutas:
                with self.subTest(usuario=usuario.email, ruta=ruta):
                    self.assertContains(self.client.get(reverse(ruta)), AVISO)
        # Filtros GET y detalle siguen disponibles.
        self.assertContains(self.client.get(reverse("comunicados:lista"), {"q": "Aviso"}), "Aviso")
        self.assertContains(self.client.get(self.comunicado.get_absolute_url()), "Texto")

    def test_aviso_visible_sin_sesion_y_head_permitido(self):
        self.assertContains(self.client.get(reverse("cuentas:iniciar_sesion")), AVISO)
        self.assertEqual(self.client.head(reverse("cuentas:iniciar_sesion")).status_code, 200)

    def test_iniciar_y_cerrar_sesion_con_csrf(self):
        cliente = cliente_demo(enforce_csrf_checks=True)
        url = reverse("cuentas:iniciar_sesion")
        datos = {"username": self.e.residente.email, "password": CLAVE}
        # Sin token CSRF el POST permitido igual se rechaza (CSRF corre antes que la demo).
        sin_token = cliente.post(url, datos)
        self.assertEqual(sin_token.status_code, 403)
        self.assertNotContains(sin_token, BLOQUEO, status_code=403)
        cliente.get(url)
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertRedirects(cliente.post(url, {**datos, "csrfmiddlewaretoken": token}), reverse("core:inicio"))
        self.assertIn("_auth_user_id", cliente.session)
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        cliente.post(reverse("cuentas:cerrar_sesion"), {"csrfmiddlewaretoken": token})
        self.assertNotIn("_auth_user_id", cliente.session)

    def test_clave_incorrecta_sigue_rechazada(self):
        respuesta = self.client.post(reverse("cuentas:iniciar_sesion"),
                                     {"username": self.e.residente.email, "password": "otra"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cambiar_condominio_conserva_pertenencia(self):
        self.client.force_login(self.e.administrador)
        ajeno = self.client.post(reverse("core:cambiar_condominio", args=[self.e.ajeno.pk]))
        self.assertEqual(ajeno.status_code, 404)
        propio = self.client.post(reverse("core:cambiar_condominio", args=[self.e.condominio.pk]))
        self.assertRedirects(propio, reverse("core:inicio"))
        self.assertEqual(self.client.session["condominio_id"], self.e.condominio.pk)

    def test_acceso_ajeno_por_rol_y_condominio(self):
        ajeno = Comunicado.objects.create(condominio=self.e.ajeno, autor=self.e.administrador,
                                          titulo="Ajeno", contenido="Reservado")
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(ajeno.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("condominios:unidades")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)  # admin: solo superusuario

    def test_escrituras_de_negocio_bloqueadas_sin_cambios(self):
        superusuario = crear_usuario("plataforma@prueba.cl", is_staff=True, is_superuser=True)
        intentos = [
            (self.e.administrador, "post", reverse("comunicados:nuevo"),
             {"titulo": "Nuevo", "contenido": "x", "tipo": Comunicado.Tipo.GENERAL}),
            (self.e.administrador, "post", reverse("comunicados:eliminar", args=[self.comunicado.pk]), {}),
            (self.e.administrador, "post", reverse("cuentas:usuario_nuevo"), {"email": "nuevo@prueba.cl"}),
            (self.e.residente, "post", reverse("comunicados:marcar_leido", args=[self.comunicado.pk]), {}),
            (self.e.residente, "post", reverse("notificaciones:marcar_todas_leidas"), {}),
            (self.e.residente, "post", reverse("cuentas:perfil"), {"first_name": "Otro"}),
            (self.e.residente, "post", reverse("cuentas:cambiar_clave"),
             {"old_password": CLAVE, "new_password1": "Otra-clave-larga-9", "new_password2": "Otra-clave-larga-9"}),
            (None, "post", reverse("cuentas:recuperar_clave"), {"email": self.e.residente.email}),
            (superusuario, "post", reverse("admin:cuentas_usuario_add"), {"email": "admin@prueba.cl"}),
            (superusuario, "post", reverse("admin:comunicados_comunicado_delete", args=[self.comunicado.pk]),
             {"post": "yes"}),
        ]
        intentos += [(self.e.administrador, metodo, self.comunicado.get_absolute_url(), {})
                     for metodo in ("put", "patch", "delete")]
        antes = foto_negocio()
        for usuario, metodo, url, datos in intentos:
            with self.subTest(metodo=metodo, url=url):
                self.client.logout()
                if usuario:
                    self.client.force_login(usuario)
                self.assertBloqueada(getattr(self.client, metodo)(url, datos))
        self.assertEqual(foto_negocio(), antes)
        self.assertEqual(mail.outbox, [])

    def test_abrir_notificacion_no_la_marca_leida(self):
        self.client.force_login(self.e.residente)
        self.assertBloqueada(self.client.get(reverse("notificaciones:abrir", args=[self.notificacion.pk])))
        self.notificacion.refresh_from_db()
        self.assertFalse(self.notificacion.leida)
        # El listado y el detalle siguen disponibles por la navegación habitual.
        self.assertContains(self.client.get(reverse("notificaciones:lista")), "Aviso")

    def test_ningun_get_sin_parametros_escribe_datos_de_negocio(self):
        rutas = rutas_sin_parametros()
        self.assertIn("comunicados:lista", rutas)
        superusuario = crear_usuario("plataforma@prueba.cl", is_staff=True, is_superuser=True)
        for usuario in (self.e.administrador, self.e.residente, superusuario):
            self.client.force_login(usuario)
            antes = foto_negocio()
            for ruta in rutas:
                with self.subTest(usuario=usuario.email, ruta=ruta):
                    self.assertLess(self.client.get(reverse(ruta)).status_code, 500)
            self.assertEqual(foto_negocio(), antes, usuario.email)


@override_settings(MIDDLEWARE=MIDDLEWARE_NORMAL)
class EntornoHabitualSinBloqueoTest(TestCase):
    """Sin settings_render_demo no hay aviso ni bloqueo: el proyecto se comporta como siempre."""

    def setUp(self):
        self.client = cliente_demo()
        self.e = crear_escenario()

    def test_escrituras_y_abrir_notificacion_funcionan(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("comunicados:nuevo"),
                                     {"titulo": "Nuevo", "contenido": "x", "tipo": Comunicado.Tipo.GENERAL})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Comunicado.objects.filter(titulo="Nuevo").exists())
        self.assertNotContains(self.client.get(reverse("core:inicio")), AVISO)
        notificacion = Notificacion.objects.create(usuario=self.e.residente, condominio=self.e.condominio,
                                                   titulo="Aviso", mensaje="x")
        self.client.force_login(self.e.residente)
        self.client.get(reverse("notificaciones:abrir", args=[notificacion.pk]))
        notificacion.refresh_from_db()
        self.assertTrue(notificacion.leida)
