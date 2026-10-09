"""Pruebas de la administración de edificios, unidades y residentes (Issue #10, RF01)."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.pruebas import crear_escenario, crear_usuario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.reservas.models import Reserva

from .models import Edificio, Membresia, Residente, Unidad


class PermisosTest(TestCase):
    """Solo el administrador modifica; el comité solo ve."""

    def setUp(self):
        self.e = crear_escenario()

    def test_comite_ve_la_pagina_sin_botones(self):
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(reverse("condominios:unidades"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, reverse("condominios:edificio_nuevo"))

    def test_admin_ve_los_botones(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("condominios:unidades")), reverse("condominios:edificio_nuevo"))

    def test_comite_y_residente_no_pueden_modificar(self):
        urls = [
            reverse("condominios:edificio_nuevo"),
            reverse("condominios:edificio_editar", args=[self.e.torre_a.pk]),
            reverse("condominios:edificio_eliminar", args=[self.e.torre_a.pk]),
            reverse("condominios:unidad_nueva"),
            reverse("condominios:unidad_editar", args=[self.e.a101.pk]),
            reverse("condominios:unidad_eliminar", args=[self.e.a101.pk]),
            reverse("condominios:residente_nuevo", args=[self.e.a101.pk]),
        ]
        for usuario in (self.e.comite, self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            for url in urls:
                with self.subTest(usuario=usuario.email, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
        residente = Residente.objects.get(usuario=self.e.residente)
        self.client.force_login(self.e.comite)
        self.assertEqual(self.client.post(reverse("condominios:residente_baja", args=[residente.pk])).status_code, 403)

    def test_no_se_modifican_datos_de_otro_condominio(self):
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(reverse("condominios:edificio_editar", args=[self.e.torre_ajena.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("condominios:unidad_editar", args=[self.e.unidad_ajena.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("condominios:residente_nuevo", args=[self.e.unidad_ajena.pk])).status_code, 404)
        ajeno = Residente.objects.get(usuario=self.e.residente_ajeno)
        self.assertEqual(self.client.post(reverse("condominios:residente_baja", args=[ajeno.pk])).status_code, 404)


class EdificioTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def test_admin_crea_edificio_en_su_condominio(self):
        self.client.post(reverse("condominios:edificio_nuevo"), {"nombre": "Torre C"})
        self.assertEqual(Edificio.objects.get(nombre="Torre C").condominio, self.e.condominio)

    def test_no_se_repite_el_nombre_en_el_condominio(self):
        respuesta = self.client.post(reverse("condominios:edificio_nuevo"), {"nombre": "torre a"})
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_el_mismo_nombre_sirve_en_otro_condominio(self):
        self.client.post(reverse("condominios:edificio_nuevo"), {"nombre": "Torre única"})
        self.assertTrue(Edificio.objects.filter(condominio=self.e.condominio, nombre="Torre única").exists())

    def test_editar_conservando_su_nombre(self):
        url = reverse("condominios:edificio_editar", args=[self.e.torre_a.pk])
        self.client.post(url, {"nombre": "Torre A", "direccion": "Pasaje 5"})
        self.e.torre_a.refresh_from_db()
        self.assertEqual(self.e.torre_a.direccion, "Pasaje 5")

    def test_no_se_elimina_un_edificio_con_unidades(self):
        self.client.post(reverse("condominios:edificio_eliminar", args=[self.e.torre_a.pk]))
        self.assertTrue(Edificio.objects.filter(pk=self.e.torre_a.pk).exists())

    def test_se_elimina_un_edificio_vacio(self):
        vacio = Edificio.objects.create(condominio=self.e.condominio, nombre="Torre vacía")
        self.client.post(reverse("condominios:edificio_eliminar", args=[vacio.pk]))
        self.assertFalse(Edificio.objects.filter(pk=vacio.pk).exists())


class UnidadTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def datos(self, **campos):
        return {"edificio": self.e.torre_a.pk, "numero": "A103", "piso": 1, "tipo": Unidad.Tipo.DEPARTAMENTO, "alicuota": "0", **campos}

    def test_admin_crea_unidad(self):
        self.client.post(reverse("condominios:unidad_nueva"), self.datos())
        self.assertTrue(Unidad.objects.filter(edificio=self.e.torre_a, numero="A103").exists())

    def test_no_se_repite_el_numero_en_el_edificio(self):
        respuesta = self.client.post(reverse("condominios:unidad_nueva"), self.datos(numero="a101"))
        self.assertEqual(respuesta.context["form"].errors["numero"], ["Ya existe la unidad A101 en Torre A."])

    def test_el_mismo_numero_sirve_en_otro_edificio(self):
        self.client.post(reverse("condominios:unidad_nueva"), self.datos(edificio=self.e.torre_b.pk, numero="A101"))
        self.assertTrue(Unidad.objects.filter(edificio=self.e.torre_b, numero="A101").exists())

    def test_editar_no_puede_tomar_el_numero_de_otra(self):
        url = reverse("condominios:unidad_editar", args=[self.e.a102.pk])
        respuesta = self.client.post(url, self.datos(numero="A101", alicuota="0.3"))
        self.assertIn("numero", respuesta.context["form"].errors)

    def test_no_se_elige_un_edificio_de_otro_condominio(self):
        respuesta = self.client.post(reverse("condominios:unidad_nueva"), self.datos(edificio=self.e.torre_ajena.pk))
        self.assertIn("edificio", respuesta.context["form"].errors)

    def test_avisa_si_las_alicuotas_no_suman_1(self):
        respuesta = self.client.post(reverse("condominios:unidad_nueva"), self.datos(alicuota="0.1"), follow=True)
        self.assertContains(respuesta, "deberían sumar 1")

    def test_no_avisa_si_las_alicuotas_suman_1(self):
        respuesta = self.client.post(reverse("condominios:unidad_nueva"), self.datos(alicuota="0"), follow=True)
        self.assertNotContains(respuesta, "deberían sumar 1")

    def test_no_se_elimina_una_unidad_con_residentes(self):
        self.client.post(reverse("condominios:unidad_eliminar", args=[self.e.a101.pk]))
        self.assertTrue(Unidad.objects.filter(pk=self.e.a101.pk).exists())

    def test_no_se_elimina_una_unidad_con_reservas(self):
        manana = timezone.localdate() + timedelta(days=1)
        Reserva.objects.create(
            espacio=self.e.quincho, unidad=self.e.a102, solicitante=self.e.administrador,
            fecha=manana, hora_inicio="10:00", hora_fin="12:00",
        )
        self.client.post(reverse("condominios:unidad_eliminar", args=[self.e.a102.pk]))
        self.assertTrue(Unidad.objects.filter(pk=self.e.a102.pk).exists())

    def test_no_se_elimina_una_unidad_con_cobros(self):
        # Sin este control, la base de datos lo impediría con un error (on_delete=RESTRICT).
        periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=9)
        DetalleGastoComun.objects.create(periodo=periodo, unidad=self.e.a102, monto=40000, monto_fondo_reserva=2000)
        url = reverse("condominios:unidad_eliminar", args=[self.e.a102.pk])
        self.assertContains(self.client.get(url), "tiene cobros de gastos comunes")
        respuesta = self.client.post(url, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se puede eliminar")
        self.assertTrue(Unidad.objects.filter(pk=self.e.a102.pk).exists())

    def test_se_elimina_una_unidad_sin_residentes(self):
        self.client.post(reverse("condominios:unidad_eliminar", args=[self.e.a102.pk]))
        self.assertFalse(Unidad.objects.filter(pk=self.e.a102.pk).exists())


class ResidenteTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)
        self.nuevo = crear_usuario("nuevo@prueba.cl")

    def asignar(self, unidad, correo, tipo=Residente.Tipo.ARRENDATARIO):
        url = reverse("condominios:residente_nuevo", args=[unidad.pk])
        return self.client.post(url, {"correo": correo, "tipo": tipo})

    def tiene_rol_residente(self, usuario):
        return Membresia.objects.filter(
            usuario=usuario, condominio=self.e.condominio, rol=Membresia.Rol.RESIDENTE, activo=True
        ).exists()

    def test_asignar_residente_le_da_el_rol(self):
        self.asignar(self.e.a102, "NUEVO@prueba.cl")
        residente = Residente.objects.get(usuario=self.nuevo)
        self.assertEqual((residente.unidad, residente.tipo), (self.e.a102, Residente.Tipo.ARRENDATARIO))
        self.assertTrue(self.tiene_rol_residente(self.nuevo))

    def test_correo_sin_cuenta(self):
        respuesta = self.asignar(self.e.a102, "nadie@prueba.cl")
        self.assertIn("correo", respuesta.context["form"].errors)

    def test_no_se_asigna_dos_veces(self):
        respuesta = self.asignar(self.e.a101, "residente@prueba.cl")
        self.assertIn("correo", respuesta.context["form"].errors)

    def test_baja_conserva_el_registro_y_quita_el_rol(self):
        residente = Residente.objects.get(usuario=self.e.residente)
        self.client.post(reverse("condominios:residente_baja", args=[residente.pk]))
        residente.refresh_from_db()
        self.assertFalse(residente.activo)
        self.assertFalse(self.tiene_rol_residente(self.e.residente))

    def test_baja_mantiene_el_rol_si_vive_en_otra_unidad(self):
        self.asignar(self.e.a102, "residente@prueba.cl")
        residente = Residente.objects.get(usuario=self.e.residente, unidad=self.e.a101)
        self.client.post(reverse("condominios:residente_baja", args=[residente.pk]))
        self.assertTrue(self.tiene_rol_residente(self.e.residente))

    def test_reasignar_despues_de_la_baja(self):
        residente = Residente.objects.get(usuario=self.e.residente)
        self.client.post(reverse("condominios:residente_baja", args=[residente.pk]))
        self.asignar(self.e.a101, "residente@prueba.cl", tipo=Residente.Tipo.FAMILIAR)
        residente.refresh_from_db()
        self.assertTrue(residente.activo)
        self.assertEqual(residente.tipo, Residente.Tipo.FAMILIAR)
        self.assertTrue(self.tiene_rol_residente(self.e.residente))

    def test_baja_solo_por_post(self):
        residente = Residente.objects.get(usuario=self.e.residente)
        self.assertEqual(self.client.get(reverse("condominios:residente_baja", args=[residente.pk])).status_code, 405)

    def test_suma_de_alicuotas_del_escenario(self):
        self.assertEqual(self.e.condominio.suma_alicuotas(), Decimal("1"))
