from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario

from .models import Proveedor

# RUT válido (el de ejemplo de validadores.py) y otro válido distinto.
RUT_1 = "12345678-5"
RUT_2 = "11111111-1"


def datos(rut=RUT_1, **extra):
    base = {"rut": rut, "razon_social": "Ascensores Sur", "rubro": "Ascensores"}
    base.update(extra)
    return base


class ProveedorTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def crear(self, condominio=None, rut=RUT_1):
        return Proveedor.objects.create(
            condominio=condominio or self.e.condominio, rut=rut, razon_social="X", rubro="Y"
        )

    # --- Lo que debe funcionar ---
    def test_administrador_crea_proveedor_y_el_rut_queda_normalizado(self):
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("proveedores:nuevo"), datos(rut="12.345.678-5"))
        proveedor = Proveedor.objects.get()
        self.assertEqual(proveedor.rut, RUT_1)
        self.assertEqual(proveedor.condominio, self.e.condominio)

    def test_comite_puede_ver_la_lista(self):
        self.crear()
        self.client.force_login(self.e.comite)
        self.assertEqual(self.client.get(reverse("proveedores:lista")).status_code, 200)

    def test_administrador_desactiva_y_reactiva(self):
        proveedor = self.crear()
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("proveedores:estado", args=[proveedor.pk]))
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)
        self.client.post(reverse("proveedores:estado", args=[proveedor.pk]))
        proveedor.refresh_from_db()
        self.assertTrue(proveedor.activo)

    # --- Validaciones del RUT ---
    def test_rut_invalido_es_rechazado(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("proveedores:nuevo"), datos(rut="12345678-9"))
        self.assertIn("rut", respuesta.context["form"].errors)
        self.assertEqual(Proveedor.objects.count(), 0)

    def test_rut_repetido_en_el_mismo_condominio_es_rechazado(self):
        self.crear()
        self.client.force_login(self.e.administrador)
        # Con puntos, para comprobar que también se detecta tras normalizar.
        respuesta = self.client.post(reverse("proveedores:nuevo"), datos(rut="12.345.678-5"))
        self.assertIn("rut", respuesta.context["form"].errors)
        self.assertEqual(Proveedor.objects.count(), 1)

    def test_mismo_rut_en_otro_condominio_es_valido(self):
        self.crear(condominio=self.e.ajeno)
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("proveedores:nuevo"), datos())
        self.assertEqual(Proveedor.objects.filter(condominio=self.e.condominio).count(), 1)

    def test_al_editar_se_puede_conservar_el_propio_rut(self):
        proveedor = self.crear()
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("proveedores:editar", args=[proveedor.pk]), datos(razon_social="Nuevo nombre"))
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.razon_social, "Nuevo nombre")

    # --- Lo que un rol NO debe poder hacer ---
    def test_comite_no_puede_crear_ni_desactivar(self):
        proveedor = self.crear()
        self.client.force_login(self.e.comite)
        self.assertEqual(self.client.get(reverse("proveedores:nuevo")).status_code, 403)
        self.assertEqual(self.client.post(reverse("proveedores:estado", args=[proveedor.pk])).status_code, 403)

    def test_residente_y_conserje_no_ven_la_lista(self):
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("proveedores:lista")).status_code, 403)

    # --- Aislamiento entre condominios ---
    def test_no_se_ven_proveedores_de_otro_condominio(self):
        self.crear(condominio=self.e.ajeno)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("proveedores:lista"))
        self.assertEqual(len(respuesta.context["proveedores"]), 0)

    def test_no_se_puede_editar_ni_desactivar_proveedor_ajeno(self):
        ajeno = self.crear(condominio=self.e.ajeno)
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(reverse("proveedores:editar", args=[ajeno.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("proveedores:estado", args=[ajeno.pk])).status_code, 404)