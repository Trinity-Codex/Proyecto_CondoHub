"""Pruebas de la administración de edificios, unidades y residentes (Issue #10, RF01)."""
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module

from django.apps import apps as registro_apps
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.pruebas import crear_escenario, crear_usuario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.gastos.reportes import generar_reporte
from apps.reservas.models import Reserva

from .models import Edificio, Membresia, Residente, Unidad
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
