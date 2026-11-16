"""Pulido visual de proveedores (Issue #97): formulario en grilla e insignias de estado."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario

from .models import Proveedor

CAMPOS = ["rut", "razon_social", "rubro", "contacto", "telefono", "correo"]


class FormularioEnGrillaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def test_los_seis_campos_van_en_media_columna_con_su_ayuda_enlazada(self):
        respuesta = self.client.get(reverse("proveedores:nuevo"))
        self.assertContains(respuesta, 'class="col-md-6"', count=len(CAMPOS))
        for nombre in CAMPOS:
            with self.subTest(campo=nombre):
                # Si el campo tiene ayuda, el control la referencia con aria-describedby.
                self.assertContains(respuesta, f'id="id_{nombre}_helptext"')
                self.assertContains(respuesta, f'<label class="form-label" for="id_{nombre}">')

    def test_los_errores_siguen_enlazados_al_campo(self):
        respuesta = self.client.post(reverse("proveedores:nuevo"), {"rut": "12345678-9"})
        self.assertContains(respuesta, 'id="id_rut_error"')
        self.assertContains(respuesta, 'id="id_razon_social_error"')
        self.assertContains(respuesta, 'id="id_rubro_error"')
        self.assertEqual(Proveedor.objects.count(), 0)

    def test_la_lista_usa_las_insignias_del_sistema(self):
        Proveedor.objects.create(condominio=self.e.condominio, rut="12345678-5", razon_social="A", rubro="X")
        Proveedor.objects.create(
            condominio=self.e.condominio, rut="11111111-1", razon_social="B", rubro="Y", activo=False
        )
        respuesta = self.client.get(reverse("proveedores:lista"))
        self.assertContains(respuesta, '<span class="insignia insignia-al-dia">Activo</span>', html=True)
        self.assertContains(respuesta, '<span class="insignia">Inactivo</span>', html=True)
        self.assertContains(respuesta, "12.345.678-5")
        self.assertNotContains(respuesta, "badge text-bg")
