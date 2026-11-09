"""Pruebas de la administración de edificios, unidades y residentes (Issue #10, RF01)."""
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module
from unittest import mock, skipUnless

from django.apps import apps as registro_apps
from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils import timezone

from apps.core.pruebas import crear_escenario, crear_usuario
from apps.cuentas.models import Usuario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.gastos.reportes import generar_reporte
from apps.reservas.models import Reserva

from . import importacion
from .models import Condominio, Edificio, Membresia, Residente, Unidad
from .residencias import cobros_visibles


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

    def asignar(self, unidad, correo, tipo=Residente.Tipo.ARRENDATARIO, desde="2026-03-20"):
        url = reverse("condominios:residente_nuevo", args=[unidad.pk])
        return self.client.post(url, {"correo": correo, "tipo": tipo, "desde": desde})

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

    def test_guarda_la_fecha_de_inicio(self):
        self.asignar(self.e.a102, "nuevo@prueba.cl", desde="2026-03-20")
        self.assertEqual(Residente.objects.get(usuario=self.nuevo).desde, date(2026, 3, 20))

    def test_la_fecha_de_inicio_es_obligatoria(self):
        respuesta = self.asignar(self.e.a102, "nuevo@prueba.cl", desde="")
        self.assertIn("desde", respuesta.context["form"].errors)
        self.assertFalse(Residente.objects.filter(usuario=self.nuevo).exists())

    def test_la_fecha_de_inicio_no_puede_ser_futura(self):
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.asignar(self.e.a102, "nuevo@prueba.cl", desde=manana.isoformat())
        self.assertIn("desde", respuesta.context["form"].errors)
        self.assertFalse(Residente.objects.filter(usuario=self.nuevo).exists())

    def test_hoy_si_es_una_fecha_valida(self):
        self.asignar(self.e.a102, "nuevo@prueba.cl", desde=timezone.localdate().isoformat())
        self.assertTrue(Residente.objects.filter(usuario=self.nuevo).exists())

    def test_el_formulario_propone_la_fecha_de_hoy(self):
        respuesta = self.client.get(reverse("condominios:residente_nuevo", args=[self.e.a102.pk]))
        self.assertContains(respuesta, timezone.localdate().isoformat())

    def test_reasignar_usa_la_nueva_fecha_y_quita_el_termino(self):
        residente = Residente.objects.get(usuario=self.e.residente)
        self.client.post(reverse("condominios:residente_baja", args=[residente.pk]))
        self.asignar(self.e.a101, "residente@prueba.cl", desde="2026-07-01")
        residente.refresh_from_db()
        self.assertEqual((residente.activo, residente.desde, residente.hasta), (True, date(2026, 7, 1), None))

    def test_la_pagina_unidades_muestra_la_fecha_de_inicio(self):
        Residente.objects.filter(usuario=self.e.residente).update(desde=date(2026, 3, 20))
        self.assertContains(self.client.get(reverse("condominios:unidades")), "desde 20-03-2026")

    def test_solo_el_administrador_asigna_residentes(self):
        url = reverse("condominios:residente_nuevo", args=[self.e.a102.pk])
        datos = {"correo": "nuevo@prueba.cl", "tipo": Residente.Tipo.FAMILIAR, "desde": "2026-03-20"}
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.email):
                self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(Residente.objects.filter(usuario=self.nuevo).exists())


class FechasDeResidenciaTest(TestCase):
    """Issue #46: "hasta" se mantiene coherente con "activo"."""

    def setUp(self):
        self.e = crear_escenario()
        self.residente = Residente.objects.get(usuario=self.e.residente)

    def test_dar_de_baja_guarda_la_fecha_de_hoy(self):
        self.residente.dar_de_baja()
        self.residente.refresh_from_db()
        self.assertEqual((self.residente.activo, self.residente.hasta), (False, timezone.localdate()))

    def test_desactivar_sin_dar_de_baja_tambien_la_guarda(self):
        # Es lo que ocurre al desmarcar "activo" en /admin/.
        self.residente.activo = False
        self.residente.save()
        self.residente.refresh_from_db()
        self.assertEqual(self.residente.hasta, timezone.localdate())

    def test_reactivar_limpia_la_fecha_de_termino(self):
        self.residente.dar_de_baja()
        self.residente.activo = True
        self.residente.save(update_fields=["activo"])
        self.residente.refresh_from_db()
        self.assertIsNone(self.residente.hasta)

    def test_dar_de_baja_con_inicio_futuro_no_falla(self):
        futura = timezone.localdate() + timedelta(days=10)
        Residente.objects.filter(pk=self.residente.pk).update(desde=futura)
        self.residente.refresh_from_db()
        self.residente.dar_de_baja()
        self.residente.refresh_from_db()
        self.assertEqual(self.residente.hasta, futura)

    def test_la_base_impide_terminar_antes_de_empezar(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Residente.objects.filter(pk=self.residente.pk).update(hasta=date(2019, 1, 1))


class MigracionFechasDeResidenciaTest(TestCase):
    """La migración no debe ocultarle a nadie un cobro que ya veía."""

    def setUp(self):
        self.e = crear_escenario()
        self.residente = Residente.objects.get(usuario=self.e.residente)
        self.migrar = import_module("apps.condominios.migrations.0002_fechas_de_residencia").fechar_residencias
        self.membresia = Membresia.objects.filter(
            usuario=self.e.residente, condominio=self.e.condominio, rol=Membresia.Rol.RESIDENTE
        )

    def cobro(self, anio, mes, estado=PeriodoGasto.Estado.EMITIDO):
        periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=anio, mes=mes, estado=estado)
        DetalleGastoComun.objects.create(periodo=periodo, unidad=self.e.a101, monto=1000, monto_fondo_reserva=50)

    def desde_migrado(self):
        self.migrar(registro_apps, None)
        self.residente.refresh_from_db()
        return self.residente.desde

    def test_usa_el_primer_cobro_si_es_anterior_a_la_membresia(self):
        self.membresia.update(desde=date(2026, 6, 15))
        self.cobro(2026, 3)
        self.cobro(2026, 2)
        self.assertEqual(self.desde_migrado(), date(2026, 2, 1))

    def test_usa_la_membresia_si_es_anterior_al_primer_cobro(self):
        self.membresia.update(desde=date(2025, 11, 5))
        self.cobro(2026, 2)
        self.assertEqual(self.desde_migrado(), date(2025, 11, 5))

    def test_no_cuenta_los_periodos_sin_emitir(self):
        self.membresia.update(desde=date(2026, 6, 15))
        self.cobro(2026, 2, estado=PeriodoGasto.Estado.ABIERTO)
        self.assertEqual(self.desde_migrado(), date(2026, 6, 15))

    def test_sin_datos_usa_la_fecha_de_la_migracion(self):
        self.membresia.delete()
        self.assertEqual(self.desde_migrado(), timezone.localdate())

    def test_una_fila_inactiva_queda_sin_fecha_de_termino(self):
        Residente.objects.filter(pk=self.residente.pk).update(activo=False)
        self.migrar(registro_apps, None)
        self.residente.refresh_from_db()
        self.assertIsNone(self.residente.hasta)


class CobrosVisiblesTest(TestCase):
    """Contrato C2 (Issue #46): cobros_visibles(cobros, usuario)."""

    def setUp(self):
        self.e = crear_escenario()
        self.residente = Residente.objects.get(usuario=self.e.residente)

    def fechar(self, desde, hasta=None):
        Residente.objects.filter(pk=self.residente.pk).update(desde=desde, hasta=hasta)

    def cobro(self, anio, mes, unidad=None):
        periodo, _ = PeriodoGasto.objects.get_or_create(
            condominio=self.e.condominio, anio=anio, mes=mes, defaults={"estado": PeriodoGasto.Estado.EMITIDO}
        )
        return DetalleGastoComun.objects.create(
            periodo=periodo, unidad=unidad or self.e.a101, monto=1000, monto_fondo_reserva=50
        )

    def visibles(self, usuario=None):
        return list(cobros_visibles(DetalleGastoComun.objects.order_by("periodo__anio", "periodo__mes"), usuario or self.e.residente))

    def test_llegada_a_mitad_de_mes_ve_ese_mes_completo(self):
        self.fechar(date(2026, 3, 20))
        febrero, marzo, abril = self.cobro(2026, 2), self.cobro(2026, 3), self.cobro(2026, 4)
        self.assertEqual(self.visibles(), [marzo, abril])
        self.assertNotIn(febrero, self.visibles())

    def test_el_ultimo_dia_del_mes_tambien_cuenta(self):
        self.fechar(date(2026, 3, 31))
        marzo = self.cobro(2026, 3)
        self.assertEqual(self.visibles(), [marzo])

    def test_cambio_de_anio(self):
        self.fechar(date(2025, 11, 10))
        octubre, enero = self.cobro(2025, 10), self.cobro(2026, 1)
        self.assertEqual(self.visibles(), [enero])
        self.assertNotIn(octubre, self.visibles())

    def test_un_mes_de_un_anio_anterior_no_se_confunde(self):
        self.fechar(date(2026, 3, 1))
        self.cobro(2025, 6)  # mes mayor que marzo, pero de un año anterior
        self.assertEqual(self.visibles(), [])

    def test_fecha_de_termino_ve_hasta_ese_mes_completo(self):
        self.fechar(date(2026, 1, 15), hasta=date(2026, 3, 2))
        marzo, abril = self.cobro(2026, 3), self.cobro(2026, 4)
        self.assertEqual(self.visibles(), [marzo])
        self.assertNotIn(abril, self.visibles())

    def test_termino_en_otro_anio(self):
        self.fechar(date(2025, 1, 1), hasta=date(2026, 2, 1))
        diciembre, marzo = self.cobro(2025, 12), self.cobro(2026, 3)
        self.assertEqual(self.visibles(), [diciembre])
        self.assertNotIn(marzo, self.visibles())

    def test_residente_inactivo_no_ve_los_cobros(self):
        self.cobro(2026, 3)
        self.residente.dar_de_baja()
        self.assertEqual(self.visibles(), [])

    def test_no_ve_cobros_de_otra_unidad(self):
        self.cobro(2026, 3, unidad=self.e.b101)
        self.assertEqual(self.visibles(), [])

    def test_las_fechas_se_cumplen_en_la_misma_residencia(self):
        # Vive en A101 desde 2020 y en A102 desde junio: en A102 no ve marzo.
        Residente.objects.create(usuario=self.e.residente, unidad=self.e.a102, desde=date(2026, 6, 1))
        propio, ajeno = self.cobro(2026, 3), self.cobro(2026, 3, unidad=self.e.a102)
        self.assertEqual(self.visibles(), [propio])
        self.assertNotIn(ajeno, self.visibles())

    def test_varios_residentes_no_repiten_cobros(self):
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a101, desde=date(2020, 1, 1))
        marzo = self.cobro(2026, 3)
        self.assertEqual(self.visibles(), [marzo])

    def test_el_resultado_se_puede_seguir_encadenando(self):
        marzo = self.cobro(2026, 3)
        cobros = cobros_visibles(DetalleGastoComun.objects.all(), self.e.residente)
        self.assertEqual(list(cobros.select_related("periodo").filter(unidad=self.e.a101).order_by("pk")), [marzo])


class ResidenciaEnPantallasTest(TestCase):
    """Issue #46 de punta a punta: el residente ve su período; la administración, toda la deuda."""

    def setUp(self):
        self.e = crear_escenario()
        Residente.objects.filter(usuario=self.e.residente).update(desde=date(2026, 3, 20))
        self.febrero = self.cobro(2026, 2)  # deuda de quien vivió antes
        self.marzo = self.cobro(2026, 3)

    def cobro(self, anio, mes):
        periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=anio, mes=mes, estado=PeriodoGasto.Estado.EMITIDO
        )
        return DetalleGastoComun.objects.create(periodo=periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000)

    def test_mi_cuenta_no_muestra_ni_suma_lo_anterior(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(list(respuesta.context["cobros"]), [self.marzo])
        self.assertEqual(respuesta.context["total_adeudado"], 42000)

    def test_el_detalle_de_un_cobro_anterior_responde_404(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("pagos:cobro_detalle", args=[self.febrero.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("pagos:cobro_detalle", args=[self.marzo.pk])).status_code, 200)

    def test_mi_deuda_del_inicio_sigue_la_misma_regla(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("core:inicio")).context["mi_deuda"], 42000)

    def test_quien_vive_en_otra_unidad_y_se_fue_de_esta_solo_ve_la_actual(self):
        otra = DetalleGastoComun.objects.create(
            periodo=self.marzo.periodo, unidad=self.e.a102, monto=10000, monto_fondo_reserva=500
        )
        Residente.objects.create(usuario=self.e.residente, unidad=self.e.a102, desde=date(2026, 1, 1))
        Residente.objects.get(usuario=self.e.residente, unidad=self.e.a101).dar_de_baja()
        self.client.force_login(self.e.residente)
        self.assertEqual(list(self.client.get(reverse("pagos:estado_cuenta")).context["cobros"]), [otra])

    def test_la_cobranza_muestra_la_deuda_completa_de_la_unidad(self):
        self.client.force_login(self.e.administrador)
        filas = self.client.get(reverse("pagos:cobranza")).context["filas"]
        self.assertEqual(next(f["deuda"] for f in filas if f["unidad"] == self.e.a101), 84000)

    def test_la_cuenta_de_la_unidad_muestra_todos_los_cobros(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.assertEqual(respuesta.context["total_adeudado"], 84000)

    def test_el_reporte_sigue_mostrando_la_deuda_anterior(self):
        fila = next(f for f in generar_reporte(self.marzo.periodo).filas if f.unidad == self.e.a101)
        self.assertEqual((fila.saldo, fila.deuda_anterior), (42000, 42000))

    def test_comite_residente_ve_filtrada_su_cuenta_y_completa_la_cobranza(self):
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a101, desde=date(2026, 3, 1))
        self.client.force_login(self.e.comite)
        self.assertEqual(list(self.client.get(reverse("pagos:estado_cuenta")).context["cobros"]), [self.marzo])
        self.assertEqual(self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk])).context["total_adeudado"], 84000)


# --------------------------------------------------------------------------
# Importar desde planilla (Issue #13)
# --------------------------------------------------------------------------
ENCABEZADOS = "edificio;numero;piso;tipo;alicuota;correo;nombre;apellido;rut;tipo_residente;desde"
# Reemplaza las 3 unidades del escenario (suman 1) y agrega una torre nueva: la suma sigue en 1.
PLANILLA = "\n".join([
    ENCABEZADOS,
    "Torre A;A101;1;Departamento;0,3;residente@prueba.cl;;;;Propietario;2020-01-01",
    "Torre A;A102;2;Departamento;0,2;nueva@prueba.cl;Nueva;Persona;11.111.111-1;Arrendatario;01-03-2024",
    "Torre A;A102;2;Departamento;0,2;hijo@prueba.cl;Hijo;Persona;22.222.222-2;Familiar;2024-03-01",
    "Torre B;B101;1;Departamento;0,3;;;;;;",
    "Torre C;C101;1;Bodega;0,2;;;;;;",
])


class ImportacionTest(TestCase):
    """Leer, validar y aplicar la planilla, sin pasar por las vistas."""

    def setUp(self):
        self.e = crear_escenario()

    def validar(self, texto):
        return importacion.validar(importacion.leer(texto), self.e.condominio)

    def errores(self, *filas):
        resultado = self.validar("\n".join([ENCABEZADOS, *filas]))
        return [e for f in resultado.filas for e in f.errores], resultado

    def importar(self, texto=PLANILLA):
        resultado = self.validar(texto)
        self.assertTrue(resultado.valido, [f.errores for f in resultado.filas] + resultado.errores_globales)
        return importacion.aplicar(resultado, self.e.condominio)

    def foto(self):
        """Todo lo que la importación puede crear o cambiar, para comparar antes y después."""
        return (
            sorted(Edificio.objects.values_list("condominio_id", "nombre")),
            sorted(Unidad.objects.values_list("edificio__nombre", "numero", "piso", "tipo", "alicuota")),
            sorted(Residente.objects.values_list("usuario__email", "unidad__numero", "tipo", "activo", "desde")),
            sorted(Membresia.objects.values_list("usuario__email", "condominio_id", "rol", "activo")),
            sorted(Usuario.objects.values_list("email", flat=True)),
        )

    def test_lee_coma_y_punto_y_coma_y_ambas_codificaciones(self):
        texto = 'edificio,numero,alicuota\nTorre Ñ,1,"0,5"'
        for contenido in (texto.encode("utf-8"), ("﻿" + texto).encode("utf-8"), texto.encode("cp1252")):
            with self.subTest(contenido=contenido[:4]):
                fila = importacion.leer(importacion.decodificar(contenido))[0]
                self.assertEqual((fila["edificio"], fila["alicuota"]), ("Torre Ñ", "0,5"))
        # Encabezados con tildes y mayúsculas, como los escribiría una persona.
        self.assertEqual(importacion.leer("Edificio;Número;Alícuota\nT;1;0,5")[0]["numero"], "1")

    def test_rechaza_un_archivo_sin_los_encabezados_o_sin_filas(self):
        for texto in ("", "nombre;correo\nAna;a@b.cl", ENCABEZADOS):
            with self.subTest(texto=texto[:10]), self.assertRaises(importacion.ArchivoInvalido):
                importacion.leer(texto)

    def test_vista_previa_con_resumen_y_sin_guardar(self):
        resultado = self.validar(PLANILLA)
        self.assertTrue(resultado.valido)
        self.assertEqual(
            resultado.resumen,
            {
                "edificios_nuevos": 1, "unidades_nuevas": 1, "unidades_actualizadas": 3,
                "cuentas_nuevas": 2, "residentes_nuevos": 2, "residentes_existentes": 1,
            },
        )
        self.assertFalse(Edificio.objects.filter(nombre="Torre C").exists())

    def test_errores_por_fila(self):
        casos = {
            "Torre A;A101;1;;0,4;x@prueba.cl;X;Y;12.345.678-9;;2024-01-01": "El RUT «12.345.678-9» no es válido.",
            "Torre A;A101;1;;0,4;x@prueba.cl;X;Y;;;2024-01-01": "Falta el dato «rut»",
            "Torre A;A101;uno;;0,4;;;;;;": "no es un número entero",
            "Torre A;A101;1;Castillo;0,4;;;;;;": "El tipo «Castillo» no existe",
            "Torre A;A101;1;;mucho;;;;;;": "La alícuota «mucho» no es un número",
            "Torre A;A101;1;;1,5;;;;;;": "entre 0 y 1",
            "Torre A;A101;1;;0,1234567;;;;;;": "hasta 6 decimales",
            "Torre A;A101;1;;0,4;residente@prueba.cl;;;;Dueño;2024-01-01": "El tipo de residente «Dueño» no existe",
            "Torre A;A101;1;;0,4;residente@prueba.cl;;;;;31-02-2024": "La fecha «31-02-2024» no es válida",
            "Torre A;A101;1;;0,4;residente@prueba.cl;;;;;": "Falta la fecha desde",
            "Torre A;A101;1;;0,4;no-es-correo;;;;;2024-01-01": "El correo «no-es-correo» no es válido.",
            ";A101;1;;0,4;;;;;;": "Falta el dato «edificio»",
        }
        for fila, error in casos.items():
            with self.subTest(fila=fila):
                errores, resultado = self.errores(fila)
                self.assertFalse(resultado.valido)
                self.assertTrue(any(error in e for e in errores), errores)
                self.assertEqual(resultado.filas_con_error[0].linea, 2)

    def test_coma_decimal_sin_comillas_no_se_pierde(self):
        resultado = self.validar("edificio,numero,alicuota\nTorre A,A101,0,4")
        self.assertIn("más valores que columnas", resultado.filas[0].errores[0])

    def test_rechaza_columnas_desconocidas(self):
        with self.assertRaisesMessage(importacion.ArchivoInvalido, "correo electronico"):
            importacion.leer("edificio;numero;alicuota;correo electronico\nT;1;0,5;a@b.cl")

    def test_cuenta_desactivada(self):
        self.e.residente.is_active = False
        self.e.residente.save()
        errores, _ = self.errores("Torre A;A101;1;;0,4;residente@prueba.cl;;;;;2020-01-01")
        self.assertIn("La cuenta de residente@prueba.cl está desactivada. Reactívala antes de importarla.", errores)

    def test_fecha_futura(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        errores, _ = self.errores(f"Torre A;A101;1;;0,4;residente@prueba.cl;;;;;{manana}")
        self.assertIn("La fecha desde no puede ser futura.", errores)

    def test_rut_de_otra_cuenta(self):
        self.e.comite.rut = "11.111.111-1"
        self.e.comite.save()
        errores, _ = self.errores("Torre A;A101;1;;0,4;x@prueba.cl;X;Y;11111111-1;;2024-01-01")
        self.assertIn("El RUT 11111111-1 ya pertenece a otra cuenta.", errores)

    def test_errores_entre_filas(self):
        ana = "Torre A;A101;1;;0,4;x@prueba.cl;Ana;Uno;11.111.111-1;;2024-01-01"
        casos = [
            (["Torre A;A101;1;;0,4;;;;;;", "torre a;a101;2;;0,4;;;;;;"], "ya aparece en la fila 2 con otro piso"),
            (["Torre A;A101;1;;0,4;residente@prueba.cl;;;;;2020-01-01"] * 2, "ya aparece como residente de esta unidad"),
            ([ana, "Torre A;A102;1;;0,3;x@prueba.cl;Ana;Otra;11.111.111-1;;2024-01-01"], "con otro nombre, apellido o RUT"),
            ([ana, "Torre A;A102;1;;0,3;y@prueba.cl;Bea;Dos;11.111.111-1;;2024-01-01"], "ya aparece con otro correo"),
        ]
        for filas, error in casos:
            with self.subTest(error=error):
                errores, _ = self.errores(*filas)
                self.assertTrue(any(error in e for e in errores), errores)

    def test_una_persona_puede_vivir_en_dos_unidades(self):
        errores, _ = self.errores(
            "Torre A;A101;1;;0,4;x@prueba.cl;Ana;Uno;11.111.111-1;;2024-01-01",
            "Torre A;A102;1;;0,3;x@prueba.cl;Ana;Uno;11.111.111-1;;2024-01-01",
        )
        self.assertEqual(errores, [])

    def test_alicuotas_que_no_suman_1(self):
        resultado = self.validar(f"{ENCABEZADOS}\nTorre C;C1;1;;0,5;;;;;;")  # 1 + 0,5
        self.assertFalse(resultado.valido)
        self.assertIn("sumarían 1,500000 y deben sumar 1. Revisa", resultado.errores_globales[0])

    def test_importa_unidades_cuentas_y_residentes_con_su_fecha(self):
        nuevas = self.importar()
        self.assertEqual(sorted(u.email for u in nuevas), ["hijo@prueba.cl", "nueva@prueba.cl"])
        self.assertTrue(Unidad.objects.filter(edificio__nombre="Torre C", numero="C101", tipo=Unidad.Tipo.BODEGA).exists())
        self.assertEqual(Unidad.objects.get(numero="A102").piso, 2)
        nueva = Residente.objects.get(usuario__email="nueva@prueba.cl")
        self.assertEqual(
            (nueva.unidad.numero, nueva.tipo, nueva.desde), ("A102", Residente.Tipo.ARRENDATARIO, date(2024, 3, 1))
        )
        self.assertEqual(nueva.usuario.rut, "11111111-1")
        self.assertTrue(nueva.usuario.has_usable_password())  # clave aleatoria: la invitación funciona
        self.assertTrue(
            Membresia.objects.filter(
                usuario=nueva.usuario, condominio=self.e.condominio, rol=Membresia.Rol.RESIDENTE, activo=True
            ).exists()
        )
        self.assertEqual(self.e.condominio.suma_alicuotas(), 1)

    def test_no_cambia_los_datos_de_una_cuenta_existente(self):
        self.importar(PLANILLA.replace("residente@prueba.cl;;;", "residente@prueba.cl;Otro;Nombre;"))
        self.e.residente.refresh_from_db()
        self.assertEqual(self.e.residente.first_name, "residente")

    def test_reimportar_no_duplica(self):
        self.importar()
        despues_de_la_primera = self.foto()
        self.assertEqual(self.importar(), [])  # sin cuentas nuevas
        self.assertEqual(self.foto(), despues_de_la_primera)

    def test_reactiva_a_un_residente_dado_de_baja(self):
        Residente.objects.get(usuario=self.e.residente).dar_de_baja()
        self.importar()
        residente = Residente.objects.get(usuario=self.e.residente)
        self.assertTrue(residente.activo)
        self.assertIsNone(residente.hasta)

    def test_si_falla_una_fila_no_queda_nada(self):
        antes = self.foto()
        guardar = Residente.save
        llamadas = []

        def falla_la_tercera(residente, *args, **kwargs):
            llamadas.append(residente)
            if len(llamadas) == 3:
                raise IntegrityError("falla simulada")
            return guardar(residente, *args, **kwargs)

        with mock.patch.object(Residente, "save", falla_la_tercera), self.assertRaises(IntegrityError):
            self.importar()
        self.assertEqual(self.foto(), antes)

    def test_la_plantilla_se_importa(self):
        vacio = Condominio.objects.create(nombre="Vacío", direccion="x", comuna="y")
        texto = importacion.decodificar(importacion.plantilla().encode("utf-8"))
        resultado = importacion.validar(importacion.leer(texto), vacio)
        self.assertTrue(resultado.valido, [f.errores for f in resultado.filas] + resultado.errores_globales)
        self.assertEqual((resultado.resumen["unidades_nuevas"], resultado.resumen["cuentas_nuevas"]), (2, 2))


class ImportacionVistasTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("condominios:importar")

    def subir(self, texto=PLANILLA, usuario=None):
        self.client.force_login(usuario or self.e.administrador)
        archivo = SimpleUploadedFile("unidades.csv", texto.encode("utf-8"), content_type="text/csv")
        return self.client.post(self.url, {"archivo": archivo})

    def confirmar(self, invitar=False):
        return self.client.post(reverse("condominios:importar_confirmar"), {"enviar_invitaciones": "1"} if invitar else {})

    def test_vista_previa_no_guarda_y_confirmar_importa(self):
        respuesta = self.subir()
        self.assertContains(respuesta, "La planilla no tiene errores")
        self.assertFalse(Edificio.objects.filter(nombre="Torre C").exists())
        self.assertRedirects(self.confirmar(), reverse("condominios:unidades"))
        self.assertTrue(Edificio.objects.filter(nombre="Torre C").exists())
        self.assertNotIn("importacion_unidades", self.client.session)

    def test_con_errores_muestra_la_fila_y_no_se_puede_confirmar(self):
        respuesta = self.subir(f"{ENCABEZADOS}\nTorre A;A101;1;;0,4;x@prueba.cl;X;Y;12.345.678-9;;2024-01-01")
        self.assertContains(respuesta, "no se importará nada")
        self.assertContains(respuesta, "<td>2</td>", html=True)
        self.assertNotContains(respuesta, reverse("condominios:importar_confirmar"))
        self.assertRedirects(self.confirmar(), self.url)
        self.assertFalse(Usuario.objects.filter(email="x@prueba.cl").exists())

    def test_archivo_ilegible_o_muy_grande(self):
        self.assertContains(self.subir("hola;mundo\n1;2"), "Faltan las columnas")
        self.assertContains(self.subir(PLANILLA + "\n" + ";" * 1_000_000), "pesa más de 1 MB")

    def test_confirmar_revalida(self):
        self.subir()
        Unidad.objects.create(edificio=self.e.torre_b, numero="B102", alicuota=Decimal("0.1"))  # ahora sumarían 1,1
        respuesta = self.confirmar()
        self.assertContains(respuesta, "Los datos cambiaron desde la vista previa")
        self.assertFalse(Edificio.objects.filter(nombre="Torre C").exists())

    def test_invitaciones_solo_a_las_cuentas_nuevas(self):
        self.subir()
        with self.captureOnCommitCallbacks(execute=True):
            self.confirmar(invitar=True)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["hijo@prueba.cl", "nueva@prueba.cl"])

    def test_sin_la_casilla_no_se_envian_correos(self):
        self.subir()
        with self.captureOnCommitCallbacks(execute=True):
            self.confirmar()
        self.assertEqual(mail.outbox, [])

    def test_la_planilla_revisada_en_otro_condominio_no_sirve(self):
        self.subir()
        sesion = self.client.session
        sesion["importacion_unidades"] = {**sesion["importacion_unidades"], "condominio": self.e.ajeno.pk}
        sesion.save()
        self.assertRedirects(self.confirmar(), self.url)
        self.assertFalse(Edificio.objects.filter(nombre="Torre C").exists())

    def test_si_otra_persona_crea_lo_mismo_a_la_vez_no_hay_error_500(self):
        self.subir()
        with mock.patch.object(importacion, "aplicar", side_effect=IntegrityError("duplicado")):
            respuesta = self.confirmar()
        self.assertRedirects(respuesta, self.url)

    def test_plantilla_descargable(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("condominios:importar_plantilla"))
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", respuesta["Content-Disposition"])
        self.assertTrue(respuesta.content.decode("utf-8").startswith("﻿edificio;numero"))

    def test_solo_el_administrador(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            for url in (self.url, reverse("condominios:importar_plantilla")):
                with self.subTest(usuario=usuario, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
            with self.subTest(usuario=usuario, url="confirmar"):
                self.assertEqual(self.confirmar().status_code, 403)

    def test_la_pagina_unidades_enlaza_la_importacion(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("condominios:unidades")), self.url)
        self.client.force_login(self.e.comite)
        self.assertNotContains(self.client.get(reverse("condominios:unidades")), self.url)


class RutResidenteEnUnidadesTest(TestCase):
    """Issue #77: el RUT del residente se ve con puntos solo para el administrador."""

    def setUp(self):
        self.e = crear_escenario()
        self.e.residente.rut = "12345678-5"
        self.e.residente.save()

    def test_administrador_lo_ve_con_puntos(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("condominios:unidades")), "12.345.678-5")

    def test_comite_no_lo_ve(self):
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(reverse("condominios:unidades"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "12.345.678-5")
        self.assertNotContains(respuesta, "12345678-5")

    def test_residente_recibe_403(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("condominios:unidades")).status_code, 403)


class FiltroOcupacionTest(TestCase):
    """Chips y ?ocupacion= del listado de unidades (Issue #80)."""

    def setUp(self):
        # A101 y B101 tienen un residente activo; A102 no tiene ninguno.
        self.e = crear_escenario()
        self.url = reverse("condominios:unidades")
        self.client.force_login(self.e.administrador)

    def numeros(self, respuesta):
        return [u.numero for edificio in respuesta.context["edificios"] for u in edificio.unidades.all()]

    def cantidades(self, respuesta):
        return {c["valor"]: c["cantidad"] for c in respuesta.context["chips"]}

    def test_cada_valor_filtra_y_los_chips_cuentan_ambos_grupos(self):
        respuesta = self.client.get(self.url, {"ocupacion": "sin_residentes"})
        self.assertEqual(self.numeros(respuesta), ["A102"])
        self.assertEqual(self.cantidades(respuesta), {"": 3, "con_residentes": 2, "sin_residentes": 1})
        respuesta = self.client.get(self.url, {"ocupacion": "con_residentes"})
        self.assertEqual(self.numeros(respuesta), ["A101", "B101"])
        self.assertContains(respuesta, "Limpiar filtros")

    def test_valor_desconocido_se_ignora(self):
        respuesta = self.client.get(self.url, {"ocupacion": "xyz"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.numeros(respuesta), ["A101", "A102", "B101"])
        self.assertNotContains(respuesta, "Limpiar filtros")

    def test_el_orden_de_las_unidades_no_cambia(self):
        self.assertEqual(self.numeros(self.client.get(self.url)), ["A101", "A102", "B101"])

    def test_una_unidad_con_dos_residentes_cuenta_una_vez(self):
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a101, desde=date(2020, 1, 1))
        respuesta = self.client.get(self.url)
        self.assertEqual(self.cantidades(respuesta), {"": 3, "con_residentes": 2, "sin_residentes": 1})

    def test_un_residente_dado_de_baja_no_cuenta_como_ocupacion(self):
        Residente.objects.filter(unidad=self.e.b101).update(activo=False, hasta=date(2024, 1, 1))
        respuesta = self.client.get(self.url, {"ocupacion": "sin_residentes"})
        self.assertEqual(self.numeros(respuesta), ["A102", "B101"])

    def test_cuadra_con_el_panel_de_inicio(self):
        """Los residentes vigentes del panel son los de las unidades «Con residentes» del listado."""
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a101, desde=date(2020, 1, 1))
        Residente.objects.filter(unidad=self.e.b101).update(activo=False, hasta=date(2024, 1, 1))
        panel = self.client.get(reverse("core:inicio")).context["resumen"]
        lista = self.client.get(self.url, {"ocupacion": "con_residentes"})
        residentes_listados = sum(len(u.residentes.all()) for e in lista.context["edificios"] for u in e.unidades.all())
        self.assertEqual(panel["residentes"], residentes_listados)
        self.assertEqual(panel["unidades"], self.cantidades(lista)[""])
        self.assertEqual(
            self.cantidades(lista)["con_residentes"] + self.cantidades(lista)["sin_residentes"], panel["unidades"]
        )
        self.assertEqual(self.cantidades(lista)["con_residentes"], 1)  # solo A101 sigue ocupada

    def test_aislamiento_otro_condominio_no_suma(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(self.cantidades(respuesta)[""], 3)
        self.assertNotContains(respuesta, "Torre única")

    def test_una_sola_consulta_cuenta_las_ocupaciones(self):
        self.client.get(self.url)  # calienta cachés
        with CaptureQueriesContext(connection) as con_filtro:
            self.client.get(self.url, {"ocupacion": "sin_residentes"})
        with CaptureQueriesContext(connection) as sin_filtro:
            self.client.get(self.url)
        self.assertEqual(len(con_filtro), len(sin_filtro))
        self.assertEqual(len([q for q in sin_filtro if "GROUP BY" in q["sql"]]), 1)

    def test_conserje_y_residente_reciben_403_con_filtros(self):
        for usuario in (self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url, {"ocupacion": "sin_residentes"}).status_code, 403)


class BusquedaBase(TestCase):
    """
    Escenario de la búsqueda (Issue #82), con datos ficticios:
      - A101: Ana Pérez (RUT 12345678-5);  B101: Juan Torres (RUT 10000013-K);  A102: sin residentes.
      - Torre B: unidades «504» y «1504» sin residentes; Torre A: «TORRES1» sin residentes.
      - Otro condominio (Ajeno): unidad «504» con un residente y su propia «Ana Pérez» (RUT 11111111-1).
    """

    def setUp(self):
        self.e = crear_escenario()
        self.nombrar(self.e.residente, "Ana", "Pérez", "12345678-5")
        self.nombrar(self.e.residente_b, "Juan", "Torres", "10000013-K")
        for edificio, numero in ((self.e.torre_b, "504"), (self.e.torre_b, "1504"), (self.e.torre_a, "TORRES1")):
            Unidad.objects.create(edificio=edificio, numero=numero, alicuota=Decimal("0"))
        self.nombrar(self.e.residente_ajeno, "Ana", "Pérez", "11111111-1")
        ajena_504 = Unidad.objects.create(edificio=self.e.torre_ajena, numero="504", alicuota=Decimal("0"))
        Residente.objects.create(usuario=crear_usuario("ajena.dos@prueba.cl"), unidad=ajena_504, desde=date(2020, 1, 1))

    @staticmethod
    def nombrar(usuario, nombre, apellido, rut):
        usuario.first_name, usuario.last_name, usuario.rut = nombre, apellido, rut
        usuario.save()


class FiltrarUnidadesTest(BusquedaBase):
    """La regla de `apps/condominios/busqueda.py`, sobre las unidades del condominio activo."""

    def buscar(self, texto, ver_rut=True):
        from .busqueda import filtrar_unidades
        unidades = Unidad.objects.filter(edificio__condominio=self.e.condominio)
        return sorted(filtrar_unidades(unidades, texto, ver_rut=ver_rut).values_list("numero", flat=True))

    def test_por_numero(self):
        self.assertEqual(self.buscar("504"), ["1504", "504"])
        self.assertEqual(self.buscar("a10"), ["A101", "A102"])

    def test_por_nombre_apellido_y_varias_palabras_en_cualquier_orden(self):
        for texto in ("Ana", "pérez", "Ana Pérez", "pérez ana", "  ANA   pérez  "):
            with self.subTest(texto=texto):
                self.assertEqual(self.buscar(texto), ["A101"])
        self.assertEqual(self.buscar("ana torres"), [])  # cada palabra debe coincidir

    def test_palabras_combinan_numero_y_nombre(self):
        self.assertEqual(self.buscar("torres"), ["B101", "TORRES1"])
        self.assertEqual(self.buscar("torres b1"), ["B101"])

    def test_rut_con_y_sin_puntos_y_por_prefijo_para_el_administrador(self):
        for texto in ("12.345.678-5", "12345678-5", "123456785", "12345", "12.345"):
            with self.subTest(texto=texto):
                self.assertEqual(self.buscar(texto), ["A101"])
        for texto in ("10.000.013-k", "10000013K"):
            with self.subTest(texto=texto):
                self.assertEqual(self.buscar(texto), ["B101"])

    def test_rut_es_por_prefijo_no_por_contenido(self):
        self.assertEqual(self.buscar("345678"), [])

    def test_el_comite_no_busca_por_rut(self):
        for texto in ("12.345.678-5", "123456785", "12345", "10000013-K"):
            with self.subTest(texto=texto):
                self.assertEqual(self.buscar(texto, ver_rut=False), [])
        self.assertEqual(self.buscar("Ana", ver_rut=False), ["A101"])

    def test_residente_dado_de_baja_no_hace_aparecer_su_unidad(self):
        Residente.objects.get(usuario=self.e.residente_b).dar_de_baja()
        self.assertEqual(self.buscar("Juan"), [])
        self.assertEqual(self.buscar("10000013"), [])

    def test_texto_vacio_o_con_espacios_no_filtra(self):
        todas = self.buscar("")
        self.assertEqual(len(todas), 6)
        self.assertEqual(self.buscar("   "), todas)

    def test_unidad_con_dos_residentes_no_se_duplica(self):
        self.nombrar(self.e.comite, "Pedro", "Pérez", "")
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a101, desde=date(2020, 1, 1))
        self.assertEqual(self.buscar("Pérez"), ["A101"])

    def test_comodines_de_like_se_buscan_como_texto(self):
        self.assertEqual(self.buscar("%"), [])
        self.assertEqual(self.buscar("_"), [])

    def test_nunca_agrega_otro_condominio(self):
        self.assertEqual(self.buscar("Ana Pérez"), ["A101"])
        self.assertEqual(self.buscar("11111111"), [])

    @skipUnless(connection.vendor == "mysql", "SQLite no ignora tildes; la base real y la CI usan MySQL")
    def test_ignora_tildes_y_mayusculas_en_mysql(self):
        self.assertEqual(self.buscar("perez"), ["A101"])
        self.nombrar(self.e.residente_b, "Juan", "perez", "10000013-K")
        self.assertEqual(self.buscar("PÉREZ"), ["A101", "B101"])


class ListadoConBusquedaTest(BusquedaBase):
    """`?q=` en la página Unidades: filtra, se combina con los chips, respeta roles y condominio."""

    def setUp(self):
        super().setUp()
        self.url = reverse("condominios:unidades")
        self.client.force_login(self.e.administrador)

    def numeros(self, respuesta):
        return [u.numero for edificio in respuesta.context["edificios"] for u in edificio.unidades.all()]

    def cantidades(self, respuesta):
        return {c["valor"]: c["cantidad"] for c in respuesta.context["chips"]}

    def test_filtra_por_numero_nombre_y_rut(self):
        self.assertEqual(self.numeros(self.client.get(self.url, {"q": "504"})), ["1504", "504"])
        self.assertEqual(self.numeros(self.client.get(self.url, {"q": "pérez ana"})), ["A101"])
        for rut in ("12.345.678-5", "123456785", "12345"):
            with self.subTest(rut=rut):
                self.assertEqual(self.numeros(self.client.get(self.url, {"q": rut})), ["A101"])

    def test_filtra_desde_un_caracter(self):
        self.assertEqual(self.numeros(self.client.get(self.url, {"q": "5"})), ["1504", "504"])

    def test_los_edificios_sin_coincidencias_se_siguen_mostrando(self):
        respuesta = self.client.get(self.url, {"q": "504"})
        self.assertEqual([e.nombre for e in respuesta.context["edificios"]], ["Torre A", "Torre B"])
        self.assertContains(respuesta, "Ninguna unidad con este filtro.")

    def test_busqueda_con_chips_que_cuentan_dentro_del_resultado(self):
        respuesta = self.client.get(self.url, {"q": "Torres", "ocupacion": "con_residentes"})
        self.assertEqual(self.numeros(respuesta), ["B101"])
        self.assertEqual(self.cantidades(respuesta), {"": 2, "con_residentes": 1, "sin_residentes": 1})
        self.assertTrue(respuesta.context["hay_filtros"])
        self.assertEqual(respuesta.context["url_limpiar"], "?")
        # Los chips conservan q y el formulario conserva ocupacion.
        chip_sin = [c for c in respuesta.context["chips"] if c["valor"] == "sin_residentes"][0]
        self.assertEqual(chip_sin["url"], "?q=Torres&ocupacion=sin_residentes")
        self.assertContains(respuesta, '<input type="hidden" name="ocupacion" value="con_residentes">', html=True)

    def test_busqueda_vacia_muestra_todo_sin_limpiar_filtros(self):
        for q in ("", "   "):
            with self.subTest(q=q):
                respuesta = self.client.get(self.url, {"q": q})
                self.assertEqual(len(self.numeros(respuesta)), 6)
                self.assertFalse(respuesta.context["hay_filtros"])
                self.assertNotContains(respuesta, "Limpiar filtros")

    def test_con_q_aparece_limpiar_filtros_que_quita_q(self):
        respuesta = self.client.get(self.url, {"q": "504"})
        self.assertContains(respuesta, "Limpiar filtros")
        self.assertEqual(respuesta.context["url_limpiar"], "?")

    def test_aislamiento_otro_condominio_nunca_aparece(self):
        for q in ("504", "Ana", "Pérez", "11111111-1"):
            with self.subTest(q=q):
                respuesta = self.client.get(self.url, {"q": q})
                self.assertNotContains(respuesta, "Torre única")
                self.assertNotContains(respuesta, "11.111.111-1")
                pks = [u.pk for e in respuesta.context["edificios"] for u in e.unidades.all()]
                self.assertNotIn(self.e.unidad_ajena.pk, pks)
        self.assertEqual(self.numeros(self.client.get(self.url, {"q": "11111111-1"})), [])
        self.assertEqual(self.cantidades(self.client.get(self.url, {"q": "504"}))[""], 2)

    def test_conserje_y_residente_reciben_403(self):
        for usuario in (self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario.email):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url, {"q": "504"}).status_code, 403)

    def test_el_comite_no_encuentra_por_rut_ni_ve_ningun_rut(self):
        self.client.force_login(self.e.comite)
        for q in ("12.345.678-5", "123456785", "12345"):
            with self.subTest(q=q):
                self.assertEqual(self.numeros(self.client.get(self.url, {"q": q})), [])
        respuesta = self.client.get(self.url, {"q": "Ana"})
        self.assertEqual(self.numeros(respuesta), ["A101"])
        for rut in ("12.345.678-5", "12345678-5", "10.000.013-K", "10000013-K"):
            self.assertNotContains(respuesta, rut)

    def test_formulario_con_el_valor_y_la_ayuda_por_rol(self):
        respuesta = self.client.get(self.url, {"q": "  pérez   ana "})
        self.assertContains(respuesta, 'role="search"')
        self.assertContains(respuesta, '<label for="busqueda-unidades" class="form-label fw-semibold">Buscar unidad o residente</label>', html=True)
        self.assertContains(respuesta, 'value="pérez ana"')
        self.assertContains(respuesta, 'maxlength="100"')
        self.assertContains(respuesta, f'data-busqueda="{reverse("condominios:unidades_sugerencias")}"')
        self.assertContains(respuesta, 'aria-live="polite"')
        self.assertContains(respuesta, "Número de unidad, nombre o RUT.")
        self.assertNotContains(respuesta, '<input type="hidden" name="ocupacion"')
        self.assertNotContains(respuesta, "{#")  # ningún comentario de plantilla a la vista
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Número de unidad o nombre.")
        self.assertNotContains(respuesta, "Número de unidad, nombre o RUT.")

    def test_la_pagina_carga_busqueda_js(self):
        self.assertContains(self.client.get(self.url), "js/busqueda.js")

    def test_la_busqueda_no_agrega_consultas_por_unidad(self):
        self.client.get(self.url)  # calienta cachés
        with CaptureQueriesContext(connection) as sin_q:
            self.client.get(self.url)
        with self.assertNumQueries(len(sin_q)):
            self.client.get(self.url, {"q": "a 1"})
        for numero in ("A201", "A202", "A203"):
            unidad = Unidad.objects.create(edificio=self.e.torre_a, numero=numero, alicuota=Decimal("0"))
            Residente.objects.create(usuario=crear_usuario(f"{numero}@prueba.cl"), unidad=unidad, desde=date(2020, 1, 1))
        with self.assertNumQueries(len(sin_q)):
            self.client.get(self.url, {"q": "a 2", "ocupacion": "con_residentes"})


class SugerenciasUnidadesTest(BusquedaBase):
    """Endpoint JSON `condominios:unidades_sugerencias` (Issue #82)."""

    def setUp(self):
        super().setUp()
        self.url = reverse("condominios:unidades_sugerencias")
        self.client.force_login(self.e.administrador)

    def pedir(self, q):
        return self.client.get(self.url, {"q": q})

    def test_administrador_recibe_nombre_y_rut_con_puntos(self):
        respuesta = self.pedir("Pér")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(respuesta.json(), {
            "resultados": [{"edificio": "Torre A", "unidad": "A101", "residentes": [{"nombre": "Ana Pérez", "rut": "12.345.678-5"}]}],
            "hay_mas": False,
        })

    def test_administrador_encuentra_por_rut_con_y_sin_puntos(self):
        for q in ("12.345.678-5", "123456785", "12345"):
            with self.subTest(q=q):
                self.assertEqual([r["unidad"] for r in self.pedir(q).json()["resultados"]], ["A101"])

    def test_comite_recibe_el_nombre_sin_ninguna_clave_rut(self):
        self.client.force_login(self.e.comite)
        self.assertEqual(self.pedir("Pér").json(), {
            "resultados": [{"edificio": "Torre A", "unidad": "A101", "residentes": [{"nombre": "Ana Pérez"}]}],
            "hay_mas": False,
        })
        datos = self.pedir("10").json()
        self.assertEqual([r["unidad"] for r in datos["resultados"]], ["A101", "A102", "B101"])
        for resultado in datos["resultados"]:
            self.assertEqual(set(resultado), {"edificio", "unidad", "residentes"})
            for residente in resultado["residentes"]:
                self.assertEqual(set(residente), {"nombre"})
        self.assertNotIn("rut", self.pedir("Juan").content.decode())

    def test_comite_no_encuentra_por_rut(self):
        self.client.force_login(self.e.comite)
        for q in ("12.345.678-5", "123456785", "12345", "10000013-K"):
            with self.subTest(q=q):
                self.assertEqual(self.pedir(q).json(), {"resultados": [], "hay_mas": False})

    def test_unidad_sin_residentes_y_sin_ids(self):
        datos = self.pedir("TORRES1").json()
        self.assertEqual(datos["resultados"], [{"edificio": "Torre A", "unidad": "TORRES1", "residentes": []}])
        texto = self.pedir("Ana").content.decode()
        self.assertNotIn('"pk"', texto)
        self.assertNotIn('"id"', texto)

    def test_sin_cache(self):
        cache = self.pedir("Ana")["Cache-Control"]
        for directiva in ("no-store", "no-cache", "must-revalidate", "private", "max-age=0"):
            self.assertIn(directiva, cache)
        self.assertIn("no-store", self.pedir("")["Cache-Control"])

    def test_menos_de_dos_caracteres_devuelve_vacio_sin_consultar_unidades(self):
        for q in ("", "P", "  P  ", "   "):
            with self.subTest(q=q):
                with CaptureQueriesContext(connection) as consultas:
                    respuesta = self.pedir(q)
                self.assertEqual(respuesta.json(), {"resultados": [], "hay_mas": False})
                self.assertFalse([c for c in consultas if "condominios_unidad" in c["sql"]])

    def test_consultas_fijas_sin_importar_la_cantidad_de_resultados(self):
        self.pedir("P")  # calienta cachés
        with CaptureQueriesContext(connection) as base:
            self.pedir("P")
        # Unidades con su edificio (1) y residentes activos con su usuario (1): nada por unidad.
        with self.assertNumQueries(len(base) + 2):
            self.assertEqual(len(self.pedir("Ana").json()["resultados"]), 1)
        with self.assertNumQueries(len(base) + 2):
            self.assertEqual(len(self.pedir("10").json()["resultados"]), 3)

    def test_tope_de_diez_en_el_orden_del_listado_y_hay_mas(self):
        torre_c = Edificio.objects.create(condominio=self.e.condominio, nombre="Torre C")
        for i in range(1, 16):
            Unidad.objects.create(edificio=torre_c, numero=f"10-{i:02d}", alicuota=Decimal("0"))
        datos = self.pedir("10").json()
        self.assertTrue(datos["hay_mas"])
        self.assertEqual(
            [(r["edificio"], r["unidad"]) for r in datos["resultados"]],
            [("Torre A", "A101"), ("Torre A", "A102"), ("Torre B", "B101")]
            + [("Torre C", f"10-{i:02d}") for i in range(1, 8)],
        )
        self.assertFalse(self.pedir("Ana").json()["hay_mas"])

    def test_aislamiento_otro_condominio_cero_resultados(self):
        for q in ("Ana Pérez", "11111111-1", "11.111.111", "Torre única", "ajena"):
            with self.subTest(q=q):
                texto = self.pedir(q).content.decode()
                self.assertNotIn("Torre única", texto)
                self.assertNotIn("11.111.111-1", texto)
        self.assertEqual([r["unidad"] for r in self.pedir("504").json()["resultados"]], ["1504", "504"])
        self.assertEqual(self.pedir("ajena").json()["resultados"], [])

    def test_conserje_y_residente_reciben_403(self):
        for usuario in (self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario.email):
                self.client.force_login(usuario)
                self.assertEqual(self.pedir("Ana").status_code, 403)

    def test_post_405_y_sin_sesion_al_inicio_de_sesion(self):
        self.assertEqual(self.client.post(self.url, {"q": "Ana"}).status_code, 405)
        self.client.logout()
        respuesta = self.pedir("Ana")
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith(resolve_url(settings.LOGIN_URL)))

    def test_residente_dado_de_baja_no_aparece(self):
        Residente.objects.get(usuario=self.e.residente).dar_de_baja()
        self.assertEqual(self.pedir("Ana").json()["resultados"], [])
        self.assertEqual(self.pedir("A101").json()["resultados"][0]["residentes"], [])
