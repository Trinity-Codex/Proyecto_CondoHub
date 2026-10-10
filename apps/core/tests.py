"""Pruebas de core: condominio activo, permisos por rol y residentes."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.condominios.models import Membresia
from apps.core.pruebas import crear_escenario, crear_usuario


class CondominioActivoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertRedirects(respuesta, reverse("cuentas:iniciar_sesion") + "?next=/", fetch_redirect_response=False)

    def test_usuario_sin_condominio(self):
        self.client.force_login(crear_usuario("nadie@prueba.cl"))
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertRedirects(respuesta, reverse("core:sin_condominio"))

    def test_toma_el_condominio_del_usuario(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.wsgi_request.condominio, self.e.condominio)
        self.assertEqual(respuesta.wsgi_request.roles, {Membresia.Rol.RESIDENTE})

    def test_no_puede_cambiar_a_un_condominio_ajeno(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("core:cambiar_condominio", args=[self.e.ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_cambiar_de_condominio(self):
        # El administrador pasa a tener acceso a los dos condominios.
        Membresia.objects.create(usuario=self.e.administrador, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("core:cambiar_condominio", args=[self.e.ajeno.pk]))
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.wsgi_request.condominio, self.e.ajeno)

    def test_panel_del_administrador_muestra_resumen(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.context["resumen"]["unidades"], 3)
        self.assertEqual(respuesta.context["suma_alicuotas"], Decimal("1"))

    def test_residente_no_ve_el_resumen(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertNotIn("resumen", respuesta.context)


class ResidenteTest(TestCase):
    def test_registrar_residente_le_da_el_rol(self):
        e = crear_escenario()
        self.assertTrue(
            Membresia.objects.filter(usuario=e.residente, condominio=e.condominio, rol=Membresia.Rol.RESIDENTE).exists()
        )

    def test_unidades_solo_para_admin_y_comite(self):
        e = crear_escenario()
        for usuario, esperado in [(e.administrador, 200), (e.comite, 200), (e.residente, 403), (e.conserje, 403)]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("condominios:unidades")).status_code, esperado, usuario)


class MenuAdministracionTest(TestCase):
    """
    Menú principal: los enlaces de gestión van en el desplegable "Administración"
    (así la barra cabe en una línea) y cada página marca solo su propio enlace.
    """

    def setUp(self):
        self.e = crear_escenario()

    def menu(self, usuario, url_name="core:inicio"):
        self.client.force_login(usuario)
        return self.client.get(reverse(url_name))

    def test_el_administrador_ve_todo_dentro_de_administracion(self):
        respuesta = self.menu(self.e.administrador)
        self.assertContains(respuesta, "Administración")
        for ruta in ("condominios:unidades", "cuentas:usuarios", "gastos:periodos", "pagos:cobranza",
                     "gastos:reporte", "proveedores:lista"):
            self.assertContains(respuesta, f'class="dropdown-item " href="{reverse(ruta)}"')

    def test_el_comite_no_ve_usuarios(self):
        respuesta = self.menu(self.e.comite)
        self.assertContains(respuesta, "Administración")
        self.assertNotContains(respuesta, reverse("cuentas:usuarios"))

    def test_residentes_y_conserje_no_ven_administracion(self):
        for usuario in (self.e.residente, self.e.conserje):
            self.assertNotContains(self.menu(usuario), "Administración")

    def test_cobranza_no_marca_mi_cuenta(self):
        # El comité de prueba también es residente: ve "Mi cuenta" y "Administración".
        Membresia.objects.create(usuario=self.e.residente, condominio=self.e.condominio, rol=Membresia.Rol.COMITE)
        respuesta = self.menu(self.e.residente, "pagos:cobranza")
        self.assertContains(respuesta, f'class="nav-link " href="{reverse("pagos:estado_cuenta")}"')
        self.assertContains(respuesta, f'class="dropdown-item active" href="{reverse("pagos:cobranza")}"')
