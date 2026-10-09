"""Pruebas del proveedor en los egresos (Issue #9, cierre): opcional y siempre del mismo condominio."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.proveedores.models import Proveedor

from .models import Egreso
from .tests import crear_egreso, crear_periodo


class EgresoProveedorTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)
        self.url_nuevo = reverse("gastos:egreso_nuevo", args=[self.periodo.pk])
        self.proveedor = Proveedor.objects.create(
            condominio=self.e.condominio, rut="76.086.428-5", razon_social="Ascensores Sur", rubro="Ascensores"
        )
        self.client.force_login(self.e.administrador)

    def datos(self, **cambios):
        return {"categoria": Egreso.Categoria.MANTENCION, "descripcion": "Mantención ascensor", "monto": "90000", "fecha": "2026-10-03", **cambios}

    def test_el_egreso_se_registra_con_proveedor(self):
        self.client.post(self.url_nuevo, self.datos(proveedor=self.proveedor.pk))
        self.assertEqual(Egreso.objects.get().proveedor, self.proveedor)

    def test_el_proveedor_es_opcional(self):
        respuesta = self.client.post(self.url_nuevo, self.datos())
        self.assertRedirects(respuesta, self.periodo.get_absolute_url())
        self.assertIsNone(Egreso.objects.get().proveedor)

    def test_solo_se_ofrecen_proveedores_activos_del_condominio(self):
        inactivo = Proveedor.objects.create(
            condominio=self.e.condominio, rut="96.511.790-K", razon_social="Jardines Viejos", rubro="Jardinería", activo=False
        )
        ajeno = Proveedor.objects.create(condominio=self.e.ajeno, rut="76.555.555-8", razon_social="De otro condominio", rubro="Aseo")
        opciones = self.client.get(self.url_nuevo).context["form"].fields["proveedor"].queryset
        self.assertEqual(list(opciones), [self.proveedor])
        # Aunque alguien envíe a mano un proveedor no permitido, el formulario lo rechaza.
        for no_permitido in (inactivo, ajeno):
            respuesta = self.client.post(self.url_nuevo, self.datos(proveedor=no_permitido.pk))
            self.assertIn("proveedor", respuesta.context["form"].errors)
        self.assertFalse(Egreso.objects.exists())

    def test_al_editar_se_conserva_un_proveedor_que_luego_se_desactivo(self):
        egreso = crear_egreso(self.periodo, self.e.administrador, proveedor=self.proveedor)
        Proveedor.objects.filter(pk=self.proveedor.pk).update(activo=False)
        url = reverse("gastos:egreso_editar", args=[egreso.pk])
        opciones = self.client.get(url).context["form"].fields["proveedor"].queryset
        self.assertEqual(list(opciones), [self.proveedor])
        self.client.post(url, self.datos(monto="95000", proveedor=self.proveedor.pk))
        egreso.refresh_from_db()
        self.assertEqual((egreso.monto, egreso.proveedor), (95000, self.proveedor))

    def test_el_periodo_muestra_el_proveedor_del_egreso(self):
        crear_egreso(self.periodo, self.e.administrador, proveedor=self.proveedor)
        respuesta = self.client.get(self.periodo.get_absolute_url())
        self.assertContains(respuesta, "Ascensores Sur")

    def test_borrar_el_proveedor_conserva_el_egreso(self):
        egreso = crear_egreso(self.periodo, self.e.administrador, proveedor=self.proveedor)
        self.proveedor.delete()
        egreso.refresh_from_db()
        self.assertIsNone(egreso.proveedor)
