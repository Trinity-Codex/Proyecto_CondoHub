"""
Pruebas de gastos comunes: períodos y egresos (Issue #1, RF02).

Cada clase corresponde a un criterio de aceptación del Issue.
"""
from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import RestrictedError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from apps.condominios.models import Unidad
from apps.core.pruebas import crear_escenario
from apps.core.templatetags.condohub import pesos

from .models import DetalleGastoComun, Egreso, PeriodoGasto, vencimiento_por_defecto


def crear_periodo(condominio, mes=10, anio=2026, **campos):
    return PeriodoGasto.objects.create(condominio=condominio, anio=anio, mes=mes, **campos)


def crear_egreso(periodo, usuario, monto=100000, **campos):
    datos = {"categoria": Egreso.Categoria.ASEO, "descripcion": "Artículos de aseo", "fecha": date(2026, 10, 5), **campos}
    return Egreso.objects.create(periodo=periodo, creado_por=usuario, monto=monto, **datos)


class PermisosTest(TestCase):
    """Criterio: solo el administrador crea, edita y elimina; el comité solo ve; residentes y conserje: 403."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)
        self.egreso = crear_egreso(self.periodo, self.e.administrador)

    def test_quien_puede_ver(self):
        for usuario, esperado in [(self.e.administrador, 200), (self.e.comite, 200), (self.e.residente, 403), (self.e.conserje, 403)]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("gastos:periodos")).status_code, esperado, usuario)
            self.assertEqual(self.client.get(self.periodo.get_absolute_url()).status_code, esperado, usuario)

    def test_quien_puede_modificar(self):
        rutas = [
            reverse("gastos:periodo_nuevo"),
            reverse("gastos:periodo_editar", args=[self.periodo.pk]),
            reverse("gastos:egreso_nuevo", args=[self.periodo.pk]),
            reverse("gastos:egreso_editar", args=[self.egreso.pk]),
            reverse("gastos:egreso_eliminar", args=[self.egreso.pk]),
        ]
        for usuario, esperado in [(self.e.administrador, 200), (self.e.comite, 403), (self.e.residente, 403), (self.e.conserje, 403)]:
            self.client.force_login(usuario)
            for ruta in rutas:
                self.assertEqual(self.client.get(ruta).status_code, esperado, f"{usuario} {ruta}")


class PeriodoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def test_abrir_periodo(self):
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA"})
        periodo = PeriodoGasto.objects.get()
        self.assertRedirects(respuesta, periodo.get_absolute_url())
        self.assertEqual(periodo.condominio, self.e.condominio)
        self.assertTrue(periodo.esta_abierto)
        self.assertEqual(str(periodo), "Octubre 2026")

    def test_no_se_repite_el_mes(self):
        crear_periodo(self.e.condominio)
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].non_field_errors())
        self.assertEqual(PeriodoGasto.objects.count(), 1)

    def test_el_mismo_mes_en_otro_condominio_si_se_puede(self):
        crear_periodo(self.e.ajeno)
        self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA"})
        self.assertEqual(PeriodoGasto.objects.filter(condominio=self.e.condominio).count(), 1)

    def test_fondo_de_reserva_minimo_5(self):
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "4", "criterio_prorrateo": "ALICUOTA"})
        self.assertIn("porcentaje_fondo_reserva", respuesta.context["form"].errors)

    def test_total_y_resumen_por_categoria(self):
        periodo = crear_periodo(self.e.condominio)
        crear_egreso(periodo, self.e.administrador, monto=300000, categoria=Egreso.Categoria.REMUNERACIONES)
        crear_egreso(periodo, self.e.administrador, monto=100000)
        respuesta = self.client.get(periodo.get_absolute_url())
        self.assertEqual(respuesta.context["total"], 400000)
        self.assertEqual(respuesta.context["por_categoria"][0]["porcentaje"], 75.0)
        self.assertContains(respuesta, "$400.000")


class EgresoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)
        self.client.force_login(self.e.administrador)

    def datos(self, **cambios):
        return {"categoria": Egreso.Categoria.CONSUMOS, "descripcion": "Luz áreas comunes", "monto": "85990", "fecha": "2026-10-03", **cambios}

    def test_registrar_egreso(self):
        respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), self.datos())
        self.assertRedirects(respuesta, self.periodo.get_absolute_url())
        egreso = Egreso.objects.get()
        self.assertEqual((egreso.periodo, egreso.creado_por, egreso.monto), (self.periodo, self.e.administrador, 85990))

    def test_editar_y_eliminar(self):
        egreso = crear_egreso(self.periodo, self.e.administrador)
        self.client.post(reverse("gastos:egreso_editar", args=[egreso.pk]), self.datos(monto="120000"))
        egreso.refresh_from_db()
        self.assertEqual(egreso.monto, 120000)
        self.client.post(reverse("gastos:egreso_eliminar", args=[egreso.pk]))
        self.assertFalse(Egreso.objects.exists())

    def test_montos_enteros_positivos(self):
        """Criterio: los montos son enteros positivos (pesos chilenos)."""
        for monto in ["0", "-500", "1500.5", "abc", "1000000000", "1.000.000.000", "0.500", "01.000", "1,5"]:
            respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), self.datos(monto=monto))
            self.assertIn("monto", respuesta.context["form"].errors, monto)
        self.assertFalse(Egreso.objects.exists())

    def test_monto_con_puntos_y_signo_se_guarda_como_entero(self):
        """Issue #76: «1.250.000» y «$ 85.000» guardan 1250000 y 85000."""
        url = reverse("gastos:egreso_nuevo", args=[self.periodo.pk])
        for texto, esperado in [("1.250.000", 1250000), ("$ 85.000", 85000), ("1250000", 1250000)]:
            self.assertRedirects(self.client.post(url, self.datos(monto=texto)), self.periodo.get_absolute_url())
            self.assertEqual(Egreso.objects.latest("pk").monto, esperado)

    def test_monto_en_el_maximo_se_acepta(self):
        url = reverse("gastos:egreso_nuevo", args=[self.periodo.pk])
        self.client.post(url, self.datos(monto="999.999.999"))
        self.assertEqual(Egreso.objects.get().monto, 999999999)

    def test_error_en_otro_campo_conserva_el_monto_con_puntos(self):
        respuesta = self.client.post(
            reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), self.datos(monto="1.250.000", descripcion="")
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'value="1.250.000"')
        self.assertFalse(Egreso.objects.exists())

    def test_monto_invalido_conserva_lo_escrito_y_explica(self):
        respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), self.datos(monto="1500.5"))
        self.assertContains(respuesta, 'value="1500.5"')
        self.assertContains(respuesta, "Escriba el monto en pesos, sin decimales")

    def test_editar_muestra_el_monto_con_puntos_y_prefijo(self):
        egreso = crear_egreso(self.periodo, self.e.administrador, monto=450000)
        respuesta = self.client.get(reverse("gastos:egreso_editar", args=[egreso.pk]))
        self.assertContains(respuesta, 'value="450.000"')
        self.assertContains(respuesta, 'data-prefijo>$')
        self.assertContains(respuesta, "data-monto")


class PeriodoEmitidoTest(TestCase):
    """Criterio: no se pueden editar egresos de un período ya emitido."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio, estado=PeriodoGasto.Estado.EMITIDO)
        self.egreso = crear_egreso(self.periodo, self.e.administrador, monto=50000)
        self.client.force_login(self.e.administrador)

    def test_no_se_agregan_egresos(self):
        respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), {
            "categoria": Egreso.Categoria.ASEO, "descripcion": "x", "monto": "1000", "fecha": "2026-10-01",
        })
        self.assertRedirects(respuesta, self.periodo.get_absolute_url())
        self.assertEqual(Egreso.objects.count(), 1)

    def test_no_se_editan_ni_eliminan(self):
        self.client.post(reverse("gastos:egreso_editar", args=[self.egreso.pk]), {
            "categoria": Egreso.Categoria.ASEO, "descripcion": "Cambiado", "monto": "1", "fecha": "2026-10-01",
        })
        self.client.post(reverse("gastos:egreso_eliminar", args=[self.egreso.pk]))
        self.egreso.refresh_from_db()  # sigue existiendo y sin cambios
        self.assertEqual((self.egreso.descripcion, self.egreso.monto), ("Artículos de aseo", 50000))

    def test_no_se_edita_el_periodo(self):
        respuesta = self.client.get(reverse("gastos:periodo_editar", args=[self.periodo.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_el_detalle_no_muestra_botones_de_edicion(self):
        respuesta = self.client.get(self.periodo.get_absolute_url())
        self.assertNotContains(respuesta, reverse("gastos:egreso_nuevo", args=[self.periodo.pk]))
        self.assertContains(respuesta, "ya fue emitido")


class MultiCondominioTest(TestCase):
    """Criterio: un condominio no ve los períodos ni egresos de otro."""

    def setUp(self):
        self.e = crear_escenario()
        self.ajeno = crear_periodo(self.e.ajeno)
        self.egreso_ajeno = crear_egreso(self.ajeno, self.e.residente_ajeno)
        crear_periodo(self.e.condominio, mes=9)
        self.client.force_login(self.e.administrador)

    def test_la_lista_solo_muestra_los_propios(self):
        periodos = list(self.client.get(reverse("gastos:periodos")).context["periodos"])
        self.assertEqual([p.condominio for p in periodos], [self.e.condominio])

    def test_no_se_accede_a_lo_ajeno(self):
        for ruta in [
            self.ajeno.get_absolute_url(),
            reverse("gastos:periodo_editar", args=[self.ajeno.pk]),
            reverse("gastos:egreso_nuevo", args=[self.ajeno.pk]),
            reverse("gastos:egreso_editar", args=[self.egreso_ajeno.pk]),
            reverse("gastos:egreso_eliminar", args=[self.egreso_ajeno.pk]),
        ]:
            self.assertEqual(self.client.get(ruta).status_code, 404, ruta)


class DetalleGastoComunTest(TestCase):
    """Modelo acordado con Winderson para el estado de cuenta (#3) y los pagos (#4)."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)

    def crear_detalle(self, unidad, monto=40000, fondo=2000):
        return DetalleGastoComun.objects.create(periodo=self.periodo, unidad=unidad, monto=monto, monto_fondo_reserva=fondo)

    def test_total_y_estado_inicial(self):
        detalle = self.crear_detalle(self.e.a101)
        self.assertEqual(detalle.total, 42000)
        self.assertEqual(detalle.estado, DetalleGastoComun.Estado.PENDIENTE)

    def test_nombres_acordados_para_navegar(self):
        """periodo.detalles y unidad.cobros: los nombres que usará Winderson."""
        detalle = self.crear_detalle(self.e.a101)
        self.assertEqual(list(self.periodo.detalles.all()), [detalle])
        self.assertEqual(list(self.e.a101.cobros.all()), [detalle])

    def test_un_solo_cobro_por_unidad_y_periodo(self):
        self.crear_detalle(self.e.a101)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear_detalle(self.e.a101)

    def test_borrar_el_periodo_borra_sus_cobros(self):
        self.crear_detalle(self.e.a101)
        self.periodo.delete()
        self.assertFalse(DetalleGastoComun.objects.exists())

    def test_no_se_borra_una_unidad_con_cobros(self):
        """Sugerencia de Maximiliano en #34: no perder las deudas ni el historial de una unidad."""
        self.crear_detalle(self.e.a101)
        with self.assertRaises(RestrictedError):
            self.e.a101.delete()
        self.assertEqual(DetalleGastoComun.objects.count(), 1)

    def test_una_unidad_sin_cobros_si_se_borra(self):
        self.crear_detalle(self.e.a101)
        self.e.a102.delete()  # A102 no tiene cobros
        self.assertFalse(Unidad.objects.filter(pk=self.e.a102.pk).exists())

    def test_borrar_todo_el_condominio_si_se_puede(self):
        """
        RESTRICT (y no PROTECT): si los cobros también se borran en la misma
        operación (por su período), se permite. Lo usa "cargar_demo --reiniciar".
        """
        self.crear_detalle(self.e.a101)
        self.e.condominio.delete()
        self.assertFalse(DetalleGastoComun.objects.exists())


class FiltroPesosTest(SimpleTestCase):
    def test_formato_chileno(self):
        self.assertEqual(pesos(1234567), "$1.234.567")
        self.assertEqual(pesos(990), "$990")
        self.assertEqual(pesos(None), "$0")
        self.assertEqual(pesos(-5000), "-$5.000")


class VencimientoYReglamentoTest(TestCase):
    """
    Issue #62 (spec gastos-comunes, «Período mensual de gastos»): vencimiento por defecto
    el día 10 del mes siguiente y referencia del reglamento si el criterio es partes iguales.
    """

    referencia = "Art. 12 del reglamento de copropiedad"

    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def abrir(self, **cambios):
        datos = {"mes": 11, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA",
                 "referencia_reglamento": "", "fecha_vencimiento": "", **cambios}
        return self.client.post(reverse("gastos:periodo_nuevo"), datos)

    def test_vencimiento_por_defecto(self):
        self.assertEqual(vencimiento_por_defecto(2026, 11), date(2026, 12, 10))
        self.assertEqual(vencimiento_por_defecto(2026, 12), date(2027, 1, 10))

    def test_el_formulario_propone_el_vencimiento_y_se_guarda(self):
        with mock.patch("apps.gastos.views.timezone.localdate", return_value=date(2026, 11, 7)):
            formulario = self.client.get(reverse("gastos:periodo_nuevo")).context["form"]
        propuesta = formulario.initial["fecha_vencimiento"]
        self.assertEqual(propuesta, date(2026, 12, 10))
        self.abrir(fecha_vencimiento=propuesta.isoformat())
        self.assertEqual(PeriodoGasto.objects.get().fecha_vencimiento, date(2026, 12, 10))

    def test_cambiar_el_mes_ajusta_el_vencimiento_propuesto(self):
        # El 7 de noviembre se propone el 10-12; el administrador abre diciembre sin tocar la fecha.
        with mock.patch("apps.gastos.views.timezone.localdate", return_value=date(2026, 11, 7)):
            respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {
                "mes": 12, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA",
                "referencia_reglamento": "", "fecha_vencimiento": "2026-12-10",
            })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(PeriodoGasto.objects.get().fecha_vencimiento, date(2027, 1, 10))

    def test_una_fecha_escrita_a_mano_no_se_cambia(self):
        with mock.patch("apps.gastos.views.timezone.localdate", return_value=date(2026, 11, 7)):
            self.client.post(reverse("gastos:periodo_nuevo"), {
                "mes": 12, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA",
                "referencia_reglamento": "", "fecha_vencimiento": "2027-01-15",
            })
        self.assertEqual(PeriodoGasto.objects.get().fecha_vencimiento, date(2027, 1, 15))

    def test_al_editar_el_mes_se_ajusta_el_vencimiento_por_defecto(self):
        periodo = crear_periodo(self.e.condominio, mes=11)  # vence el 10-12-2026
        self.client.post(reverse("gastos:periodo_editar", args=[periodo.pk]), {
            "mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA",
            "referencia_reglamento": "", "fecha_vencimiento": "2026-12-10",
        })
        periodo.refresh_from_db()
        self.assertEqual((periodo.mes, periodo.fecha_vencimiento), (10, date(2026, 11, 10)))

    def test_vencimiento_vacio_usa_el_dia_10_del_mes_siguiente(self):
        self.abrir(mes=12)
        self.assertEqual(PeriodoGasto.objects.get().fecha_vencimiento, date(2027, 1, 10))

    def test_vencimiento_dentro_del_mismo_mes_se_rechaza(self):
        respuesta = self.abrir(fecha_vencimiento="2026-11-30")
        self.assertIn("desde el 01-12-2026", respuesta.context["form"].errors["fecha_vencimiento"][0])
        self.assertFalse(PeriodoGasto.objects.exists())

    def test_el_primer_dia_del_mes_siguiente_si_se_acepta(self):
        self.abrir(fecha_vencimiento="2026-12-01")
        self.assertEqual(PeriodoGasto.objects.get().fecha_vencimiento, date(2026, 12, 1))

    def test_partes_iguales_sin_referencia_se_rechaza(self):
        respuesta = self.abrir(criterio_prorrateo="PARTES_IGUALES", referencia_reglamento="   ")
        self.assertIn("reglamento", respuesta.context["form"].errors["referencia_reglamento"][0])
        self.assertFalse(PeriodoGasto.objects.exists())

    def test_partes_iguales_con_referencia_se_guarda_y_se_muestra(self):
        self.abrir(criterio_prorrateo="PARTES_IGUALES", referencia_reglamento=self.referencia)
        respuesta = self.client.get(PeriodoGasto.objects.get().get_absolute_url())
        self.assertContains(respuesta, "En partes iguales")
        self.assertContains(respuesta, self.referencia)

    def test_la_regla_del_reglamento_tambien_vale_en_el_admin(self):
        # El /admin/ de Django llama a full_clean(): por eso la regla está en el modelo.
        periodo = PeriodoGasto(condominio=self.e.condominio, anio=2026, mes=11,
                               criterio_prorrateo=PeriodoGasto.Criterio.PARTES_IGUALES)
        with self.assertRaises(ValidationError) as error:
            periodo.full_clean()
        self.assertIn("referencia_reglamento", error.exception.message_dict)

    def test_comite_ve_el_vencimiento_y_no_puede_editar(self):
        periodo = crear_periodo(self.e.condominio, mes=11, criterio_prorrateo=PeriodoGasto.Criterio.PARTES_IGUALES,
                                referencia_reglamento=self.referencia)
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(periodo.get_absolute_url())
        self.assertContains(respuesta, "10-12-2026")
        self.assertContains(respuesta, self.referencia)
        self.assertEqual(self.client.get(reverse("gastos:periodo_nuevo")).status_code, 403)
        self.assertEqual(self.client.get(reverse("gastos:periodo_editar", args=[periodo.pk])).status_code, 403)

    def test_residente_y_conserje_reciben_403(self):
        periodo = crear_periodo(self.e.condominio, mes=11)
        rutas = [periodo.get_absolute_url(), reverse("gastos:periodo_nuevo"),
                 reverse("gastos:periodo_editar", args=[periodo.pk])]
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            for ruta in rutas:
                self.assertEqual(self.client.get(ruta).status_code, 403, f"{usuario} {ruta}")

    def test_periodo_de_otro_condominio_da_404(self):
        ajeno = crear_periodo(self.e.ajeno, mes=11)
        respuesta = self.client.post(reverse("gastos:periodo_editar", args=[ajeno.pk]), {
            "mes": 11, "anio": 2026, "porcentaje_fondo_reserva": "5", "criterio_prorrateo": "ALICUOTA",
            "fecha_vencimiento": "2026-12-15",
        })
        self.assertEqual(respuesta.status_code, 404)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.fecha_vencimiento, date(2026, 12, 10))


class MigracionVencimientoTest(TransactionTestCase):
    """Escenario «Períodos anteriores al cambio»: la migración 0006 completa el vencimiento de los períodos que ya había."""

    antes = [("gastos", "0005_egreso_proveedor")]
    despues = [("gastos", "0006_vencimiento_y_reglamento")]

    def tearDown(self):
        # Deja la base de pruebas con todas las migraciones, como la esperan las demás pruebas.
        call_command("migrate", verbosity=0)

    def test_periodos_existentes_quedan_con_el_dia_10_del_mes_siguiente(self):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(self.antes)
        estado = ejecutor.loader.project_state(self.antes).apps
        condominio = estado.get_model("condominios", "Condominio").objects.create(
            nombre="Antiguo", direccion="Calle 3", comuna="Maipú"
        )
        periodo_antiguo = estado.get_model("gastos", "PeriodoGasto")
        noviembre = periodo_antiguo.objects.create(condominio=condominio, anio=2025, mes=11)
        diciembre = periodo_antiguo.objects.create(condominio=condominio, anio=2025, mes=12)

        ejecutor = MigrationExecutor(connection)
        ejecutor.loader.build_graph()
        ejecutor.migrate(self.despues)
        periodo_nuevo = ejecutor.loader.project_state(self.despues).apps.get_model("gastos", "PeriodoGasto")
        self.assertEqual(periodo_nuevo.objects.get(pk=noviembre.pk).fecha_vencimiento, date(2025, 12, 10))
        self.assertEqual(periodo_nuevo.objects.get(pk=diciembre.pk).fecha_vencimiento, date(2026, 1, 10))
        self.assertEqual(periodo_nuevo.objects.get(pk=diciembre.pk).referencia_reglamento, "")


class FiltroEgresosTest(TestCase):
    """Chips y ?categoria= del detalle del período (Issue #80): el orden de los egresos no cambia."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)
        admin = self.e.administrador
        self.aseo_tarde = crear_egreso(self.periodo, admin, monto=30000, fecha=date(2026, 10, 20))
        self.luz = crear_egreso(
            self.periodo, admin, monto=50000, categoria=Egreso.Categoria.CONSUMOS, fecha=date(2026, 10, 10)
        )
        self.aseo_temprano = crear_egreso(self.periodo, admin, monto=20000, fecha=date(2026, 10, 2))
        self.url = reverse("gastos:periodo_detalle", args=[self.periodo.pk])
        self.client.force_login(admin)

    def test_filtra_por_categoria_y_el_total_no_cambia(self):
        respuesta = self.client.get(self.url, {"categoria": "ASEO"})
        self.assertEqual([e.pk for e in respuesta.context["egresos"]], [self.aseo_temprano.pk, self.aseo_tarde.pk])
        self.assertEqual(respuesta.context["total"], 100000)
        cantidades = {c["valor"]: c["cantidad"] for c in respuesta.context["chips"]}
        self.assertEqual(cantidades, {"": 3, "CONSUMOS": 1, "ASEO": 2})
        self.assertContains(respuesta, "(todas las categorías)")
        self.assertContains(respuesta, "Limpiar filtros")

    def test_categoria_desconocida_se_ignora(self):
        respuesta = self.client.get(self.url, {"categoria": "XYZ"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["egresos"]), 3)
        self.assertNotContains(respuesta, "Limpiar filtros")

    def test_el_orden_de_los_egresos_sigue_siendo_fecha_y_pk(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(
            [e.pk for e in respuesta.context["egresos"]], [self.aseo_temprano.pk, self.luz.pk, self.aseo_tarde.pk]
        )

    def test_aislamiento_egresos_de_otro_condominio_no_suman(self):
        ajeno = crear_periodo(self.e.ajeno)
        crear_egreso(ajeno, self.e.administrador, monto=999)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["chips"][0]["cantidad"], 3)
        self.assertEqual(respuesta.context["total"], 100000)

    def test_periodo_de_otro_condominio_da_404_con_filtro(self):
        ajeno = crear_periodo(self.e.ajeno)
        respuesta = self.client.get(reverse("gastos:periodo_detalle", args=[ajeno.pk]), {"categoria": "ASEO"})
        self.assertEqual(respuesta.status_code, 404)

    def test_residente_recibe_403(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(self.url, {"categoria": "ASEO"}).status_code, 403)

    def test_insignia_del_periodo(self):
        self.assertContains(self.client.get(reverse("gastos:periodos")), "insignia insignia-en-proceso")


class FondoManualTest(TestCase):
    """Issue #8: validación del servicio y auditoría del libro del fondo."""

    def setUp(self):
        from . import fondo
        self.fondo = fondo
        self.e = crear_escenario()

    def registrar(self, tipo="INICIAL", **cambios):
        return self.fondo.registrar_movimiento(
            self.e.condominio, tipo=tipo, usuario=self.e.administrador,
            **{"monto": 100000, "fecha": date(2026, 10, 1), "descripcion": "Respaldo ficticio de apertura",
               "acuerdo": "Acta ficticia 1", **cambios},
        )

    def test_administrador_configura_inicial_y_auditoria(self):
        from apps.auditoria.models import RegistroAuditoria
        movimiento = self.registrar(monto=0)
        self.assertEqual((movimiento.monto, movimiento.creado_por), (0, self.e.administrador))
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 0)
        evento = RegistroAuditoria.objects.get(objeto_tipo="movimientofondo")
        self.assertEqual((evento.accion, evento.usuario_id, evento.despues["monto"]), ("crear", self.e.administrador.pk, 0))

    def test_saldo_inicial_repetido(self):
        from .models import MovimientoFondo
        self.registrar()
        with self.assertRaises(ValidationError):
            self.registrar()
        self.assertEqual(MovimientoFondo.objects.count(), 1)

    def test_egreso_autorizado_y_saldo_negativo(self):
        self.registrar(monto=0)
        egreso = self.registrar("EGRESO", monto=2500)
        self.assertEqual(egreso.monto, -2500)
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), -2500)

    def test_ajuste_trazable_positivo_y_negativo(self):
        inicial = self.registrar()
        self.registrar("AJUSTE", monto=-1000)
        self.registrar("AJUSTE", monto=500)
        inicial.refresh_from_db()
        self.assertEqual(inicial.monto, 100000)
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 99500)

    def test_datos_invalidos_no_guardan_ni_auditan(self):
        from apps.auditoria.models import RegistroAuditoria
        from apps.proveedores.models import Proveedor
        from .models import MovimientoFondo, MONTO_MAXIMO
        ajeno = Proveedor.objects.create(condominio=self.e.ajeno, rut="12345678-5", razon_social="Ficticio")
        for tipo, cambios in [
            ("INICIAL", {"monto": -1}), ("EGRESO", {"monto": 0}), ("EGRESO", {"monto": -1}),
            ("AJUSTE", {"monto": 0}), ("EGRESO", {"monto": MONTO_MAXIMO + 1}),
            ("AJUSTE", {"monto": -MONTO_MAXIMO - 1}), ("EGRESO", {"descripcion": "  "}),
            ("EGRESO", {"acuerdo": "  "}), ("AJUSTE", {"acuerdo": ""}),
            ("EGRESO", {"fecha": None}), ("EGRESO", {"proveedor": ajeno}),
            ("INGRESO", {}), ("DESCONOCIDO", {}), ("EGRESO", {"monto": 1.5}),
        ]:
            with self.subTest(tipo=tipo, cambios=cambios), self.assertRaises(ValidationError):
                self.registrar(tipo, **cambios)
        self.assertFalse(MovimientoFondo.objects.exists())
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_datos_nulos_de_respaldo_son_validation_error(self):
        for cambios in [{"descripcion": None}, {"acuerdo": None}]:
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                self.registrar("EGRESO", **cambios)

    def test_fecha_de_servicio_normalizada(self):
        self.registrar("AJUSTE", monto=1)
        inicial = self.registrar(fecha="2026-10-01")
        self.assertEqual(inicial.fecha, date(2026, 10, 1))

    def test_manual_anterior_a_apertura(self):
        self.registrar()
        for tipo in ("EGRESO", "AJUSTE"):
            with self.subTest(tipo=tipo), self.assertRaises(ValidationError):
                self.registrar(tipo, fecha=date(2026, 9, 30))
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 100000)

    def test_rollback_si_falla_auditoria_manual(self):
        from .models import MovimientoFondo
        for tipo in ("INICIAL", "EGRESO", "AJUSTE"):
            with self.subTest(tipo=tipo), mock.patch("apps.gastos.fondo.registrar", side_effect=RuntimeError("C1")):
                with self.assertRaises(RuntimeError):
                    self.registrar(tipo)
            self.assertFalse(MovimientoFondo.objects.exists())
            self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 0)


class FondoConsultasTest(TestCase):
    def setUp(self):
        from . import fondo
        self.fondo = fondo
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)

    def manual(self, tipo="INICIAL", **cambios):
        return self.fondo.registrar_movimiento(self.e.condominio, tipo=tipo, usuario=self.e.administrador,
            **{"monto": 100000, "fecha": date(2026, 10, 1), "descripcion": "Respaldo ficticio", "acuerdo": "Acta 1", **cambios})

    def test_fondo_sin_movimientos(self):
        from .models import MovimientoFondo
        saldo = self.fondo.saldo_fondo(self.e.condominio)
        self.assertIs(type(saldo), int)
        self.assertEqual(saldo, 0)
        self.assertEqual(list(self.fondo.movimientos_fondo(self.e.condominio, self.periodo)), [])
        self.assertFalse(MovimientoFondo.objects.exists())

    def test_corte_inclusivo_emision_tardia_y_mes_abierto(self):
        from .servicios import emitir_periodo
        self.manual()
        crear_egreso(self.periodo, self.e.administrador, monto=100001)
        emitir_periodo(self.periodo)
        self.manual("EGRESO", monto=2000, fecha=date(2026, 10, 31))
        self.manual("EGRESO", monto=1000, fecha=date(2026, 11, 1))
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio, self.periodo), 103000)
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 102000)
        abierto = crear_periodo(self.e.condominio, mes=11)
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio, abierto), 102000)

    def test_febrero_bisiesto_y_cambio_de_anio(self):
        for anio, mes, ultimo, siguiente in [(2024, 2, date(2024, 2, 29), date(2024, 3, 1)),
                                            (2025, 12, date(2025, 12, 31), date(2026, 1, 1))]:
            periodo = crear_periodo(self.e.condominio, mes=mes, anio=anio)
            self.manual("AJUSTE", monto=10, fecha=ultimo)
            self.manual("AJUSTE", monto=20, fecha=siguiente)
            filas = list(self.fondo.movimientos_fondo(self.e.condominio, periodo))
            self.assertEqual([m.fecha for m in filas], [ultimo])
            esperado = 10 if anio == 2024 else 40
            self.assertEqual(self.fondo.saldo_fondo(self.e.condominio, periodo), esperado)

    def test_movimientos_mes_orden_relaciones_y_aislamiento(self):
        primero = self.manual()
        segundo = self.manual("AJUSTE", monto=5)
        self.manual("EGRESO", monto=1, fecha=date(2026, 11, 1))
        self.fondo.registrar_movimiento(self.e.ajeno, tipo="INICIAL", monto=999, fecha=date(2026, 10, 1), descripcion="Ajeno")
        filas = self.fondo.movimientos_fondo(self.e.condominio, self.periodo)
        with self.assertNumQueries(1):
            valores = [(m.pk, m.tipo, m.monto, m.descripcion, m.acuerdo, m.proveedor, m.periodo, m.creado_por.pk) for m in filas]
        self.assertEqual([m[0] for m in valores], [primero.pk, segundo.pk])
        self.assertEqual(self.fondo.movimientos_fondo(self.e.condominio).count(), 3)

    def test_periodo_ajeno_en_ambas_consultas(self):
        ajeno = crear_periodo(self.e.ajeno)
        for consultar in (self.fondo.saldo_fondo, self.fondo.movimientos_fondo):
            with self.subTest(consulta=consultar), self.assertRaises(ValidationError):
                consultar(self.e.condominio, ajeno)

    def test_legado_exige_apertura_y_no_duplica(self):
        self.periodo.estado = PeriodoGasto.Estado.EMITIDO
        self.periodo.save()
        cobro = DetalleGastoComun.objects.create(periodo=self.periodo, unidad=self.e.a101, monto=100, monto_fondo_reserva=5)
        for consulta in (self.fondo.saldo_fondo, self.fondo.movimientos_fondo):
            with self.assertRaises(ValidationError) as error:
                consulta(self.e.condominio)
            self.assertEqual(error.exception.code, "fondo_sin_apertura")
        with self.assertRaises(ValidationError):
            self.manual(fecha=date(2026, 10, 31))
        self.manual(fecha=date(2026, 11, 1))
        for consulta in (self.fondo.saldo_fondo, self.fondo.movimientos_fondo):
            with self.assertRaises(ValidationError) as error:
                consulta(self.e.condominio, self.periodo)
            self.assertEqual(error.exception.code, "fondo_sin_cobertura")
        cobro.refresh_from_db()
        self.assertEqual(cobro.total, 105)
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 100000)
        self.assertEqual(self.fondo.movimientos_fondo(self.e.condominio).count(), 1)

    def test_inicial_opcional_no_puede_superar_primer_movimiento(self):
        self.manual("AJUSTE", monto=5)
        with self.assertRaises(ValidationError):
            self.manual(fecha=date(2026, 10, 2))
        self.manual(fecha=date(2026, 10, 1))
        self.assertEqual(self.fondo.saldo_fondo(self.e.condominio), 100005)


class FondoEmisionTest(TestCase):
    def setUp(self):
        from .models import MovimientoFondo
        from .servicios import emitir_periodo
        from apps.auditoria.models import RegistroAuditoria
        from apps.notificaciones.models import Notificacion
        self.Movimiento = MovimientoFondo
        self.Evento = RegistroAuditoria
        self.Notificacion = Notificacion
        self.emitir = emitir_periodo
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)
        crear_egreso(self.periodo, self.e.administrador, monto=100001)

    def assert_sin_efectos(self):
        self.periodo.refresh_from_db()
        self.assertTrue(self.periodo.esta_abierto)
        self.assertFalse(DetalleGastoComun.objects.exists())
        self.assertFalse(self.Movimiento.objects.filter(tipo="INGRESO").exists())
        self.assertFalse(self.Evento.objects.filter(objeto_tipo__in=["periodogasto", "movimientofondo"]).exists())
        self.assertFalse(self.Notificacion.objects.exists())

    def test_aporte_exacto_y_auditoria_autor(self):
        from .fondo import saldo_fondo
        self.emitir(self.periodo, usuario=self.e.administrador)
        ingreso = self.Movimiento.objects.get()
        self.assertEqual(ingreso.monto, sum(self.periodo.detalles.values_list("monto_fondo_reserva", flat=True)))
        self.assertEqual((ingreso.monto, ingreso.fecha, ingreso.periodo), (5000, date(2026, 10, 31), self.periodo))
        self.assertEqual(saldo_fondo(self.e.condominio), 5000)
        evento = self.Evento.objects.get(objeto_tipo="periodogasto")
        self.assertEqual((evento.accion, evento.usuario_id, evento.antes["estado"], evento.despues["estado"]),
                         ("modificar", self.e.administrador.pk, "ABIERTO", "EMITIDO"))
        self.assertEqual(evento.despues["aporte_fondo"], 5000)
        self.assertEqual(self.Evento.objects.filter(objeto_tipo="movimientofondo").count(), 1)
        with self.assertRaises(ValidationError):
            self.emitir(self.periodo)
        self.assertEqual(self.Movimiento.objects.count(), 1)

    def test_sistema_y_aporte_redondeado_a_cero(self):
        self.periodo.egresos.update(monto=1)
        self.emitir(self.periodo)
        ingreso = self.Movimiento.objects.get()
        self.assertEqual(ingreso.monto, 0)
        self.assertIsNone(ingreso.creado_por)
        self.assertEqual(self.Evento.objects.get(objeto_tipo="periodogasto").usuario_nombre, "Sistema")

    def test_alicuotas_y_sin_egresos_no_crean_ingreso_ni_eventos(self):
        self.e.a101.alicuota = 0
        self.e.a101.save()
        with self.assertRaises(ValidationError):
            self.emitir(self.periodo)
        self.assert_sin_efectos()
        self.periodo.egresos.all().delete()
        with self.assertRaises(ValidationError):
            self.emitir(self.periodo)
        self.assert_sin_efectos()

    def test_emision_atomica_ingreso_auditoria_y_notificacion(self):
        from apps.notificaciones.models import Notificacion
        for destino in ["apps.gastos.fondo.MovimientoFondo.save", "apps.gastos.fondo.registrar", "apps.gastos.servicios.registrar"]:
            with self.subTest(destino=destino), mock.patch(destino, side_effect=RuntimeError("Fallo simulado")):
                with self.assertRaises(RuntimeError):
                    self.emitir(self.periodo)
            self.assert_sin_efectos()
        crear_notificacion = Notificacion.objects.bulk_create
        def notificar_y_fallar(*args, **kwargs):
            crear_notificacion(*args, **kwargs)
            raise RuntimeError("Notificación persistida y fallo")
        with mock.patch.object(Notificacion.objects, "bulk_create", side_effect=notificar_y_fallar):
            with self.assertRaises(RuntimeError):
                self.emitir(self.periodo)
        self.assert_sin_efectos()

    def test_emision_anterior_a_apertura(self):
        from .fondo import registrar_movimiento
        registrar_movimiento(self.e.condominio, tipo="INICIAL", monto=0, fecha=date(2026, 11, 1), descripcion="Respaldo ficticio")
        previos = self.Evento.objects.count()
        with self.assertRaises(ValidationError):
            self.emitir(self.periodo)
        self.periodo.refresh_from_db()
        self.assertTrue(self.periodo.esta_abierto)
        self.assertEqual(self.Evento.objects.count(), previos)
        self.assertFalse(DetalleGastoComun.objects.exists())
        self.assertFalse(self.Movimiento.objects.filter(tipo="INGRESO").exists())

    def test_restrict_periodo_y_cascada_condominio(self):
        self.emitir(self.periodo)
        with self.assertRaises(RestrictedError):
            self.periodo.delete()
        self.e.condominio.delete()
        self.assertFalse(self.Movimiento.objects.exists())


class FondoRestriccionesTest(TestCase):
    def setUp(self):
        from .models import MovimientoFondo
        self.Movimiento = MovimientoFondo
        self.e = crear_escenario()
        self.periodo = crear_periodo(self.e.condominio)

    def test_mysql_signos_origen_y_marca(self):
        for campos in [
            {"tipo": "INICIAL", "monto": -1, "marca_inicial": 1},
            {"tipo": "INICIAL", "monto": 1},
            {"tipo": "EGRESO", "monto": 0}, {"tipo": "EGRESO", "monto": 1},
            {"tipo": "AJUSTE", "monto": 0}, {"tipo": "INGRESO", "monto": 1},
            {"tipo": "INGRESO", "monto": -1, "periodo": self.periodo},
            {"tipo": "AJUSTE", "monto": 1, "periodo": self.periodo},
            {"tipo": "EGRESO", "monto": -1, "marca_inicial": 1}, {"tipo": "OTRO", "monto": 1},
        ]:
            with self.subTest(campos=campos), self.assertRaises(IntegrityError), transaction.atomic():
                self.Movimiento.objects.create(condominio=self.e.condominio, fecha=date(2026, 10, 1), descripcion="Ficticio", **campos)

    def test_unicidad_inicial_e_ingreso_en_base(self):
        for campos in [{"tipo": "INICIAL", "marca_inicial": 1}, {"tipo": "INGRESO", "periodo": self.periodo}]:
            datos = {"condominio": self.e.condominio, "monto": 0, "fecha": date(2026, 10, 1), "descripcion": "Ficticio", **campos}
            self.Movimiento.objects.create(**datos)
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.Movimiento.objects.create(**datos)

    def test_rechaza_periodo_y_proveedor_ajenos_en_modelo_y_servicio(self):
        from .fondo import registrar_movimiento
        ajeno = crear_periodo(self.e.ajeno)
        movimiento = self.Movimiento(condominio=self.e.condominio, tipo="INGRESO", monto=1,
            fecha=date(2026, 10, 31), descripcion="Ficticio", periodo=ajeno)
        with self.assertRaises(ValidationError):
            movimiento.full_clean()
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.e.condominio, tipo="EGRESO", monto=1, fecha=date(2026, 10, 1),
                descripcion="Ficticio", acuerdo="Acta", periodo=ajeno)


class FondoVistasTest(TestCase):
    def setUp(self):
        from .fondo import registrar_movimiento
        from .models import MovimientoFondo
        self.Movimiento = MovimientoFondo
        self.e = crear_escenario()
        self.movimiento = registrar_movimiento(self.e.condominio, tipo="INICIAL", monto=1000,
            fecha=date(2026, 10, 1), descripcion="Respaldo ficticio")
        self.ajeno = registrar_movimiento(self.e.ajeno, tipo="INICIAL", monto=999,
            fecha=date(2026, 10, 1), descripcion="Respaldo ajeno")
        self.manuales = [reverse("gastos:fondo_inicial"), reverse("gastos:fondo_egreso"), reverse("gastos:fondo_ajuste")]
        self.consultas = [reverse("gastos:fondo"), self.movimiento.get_absolute_url()]

    def datos(self, **cambios):
        return {"monto": "2.500", "fecha": "2026-10-01", "descripcion": "Mantención ficticia", "acuerdo": "Acta ficticia 1", **cambios}

    def test_comite_consulta_y_no_registra(self):
        self.client.force_login(self.e.comite)
        for ruta in self.consultas:
            self.assertEqual(self.client.get(ruta).status_code, 200)
        for ruta in self.manuales:
            self.assertEqual(self.client.get(ruta).status_code, 403)
            self.assertEqual(self.client.post(ruta, self.datos()).status_code, 403)
        self.assertEqual(self.Movimiento.objects.count(), 2)

    def test_conserje_y_residente_sin_acceso_get_post(self):
        for usuario in (self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            for ruta in self.consultas + self.manuales:
                with self.subTest(usuario=usuario, ruta=ruta):
                    self.assertEqual(self.client.get(ruta).status_code, 403)
                    self.assertEqual(self.client.post(ruta, self.datos()).status_code, 403)
        self.assertEqual(self.Movimiento.objects.count(), 2)

    def test_ajeno_404_y_excluido_para_admin_y_comite(self):
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.ajeno.get_absolute_url()).status_code, 404)
            self.assertNotContains(self.client.get(reverse("gastos:fondo")), "Respaldo ajeno")

    def test_administrador_formularios_y_asignacion_servidor(self):
        self.client.force_login(self.e.administrador)
        for ruta in self.manuales:
            self.assertEqual(self.client.get(ruta).status_code, 200)
        respuesta = self.client.post(reverse("gastos:fondo_egreso"), self.datos(
            condominio=self.e.ajeno.pk, creado_por=self.e.residente.pk))
        nuevo = self.Movimiento.objects.latest("pk")
        self.assertRedirects(respuesta, nuevo.get_absolute_url())
        self.assertEqual((nuevo.monto, nuevo.condominio, nuevo.creado_por), (-2500, self.e.condominio, self.e.administrador))
        for sentido, esperado in [("SUMAR", 2500), ("RESTAR", -2500)]:
            self.client.post(reverse("gastos:fondo_ajuste"), self.datos(sentido=sentido))
            self.assertEqual(self.Movimiento.objects.latest("pk").monto, esperado)
        self.assertContains(self.client.get(reverse("gastos:fondo")), "Saldo contable del fondo")
        self.assertContains(self.client.get(reverse("gastos:fondo")), "Saldo contable negativo")

    def test_formulario_rechaza_proveedor_ajeno_y_errores_asociados(self):
        from apps.proveedores.models import Proveedor
        self.client.force_login(self.e.administrador)
        proveedor = Proveedor.objects.create(condominio=self.e.ajeno, rut="12345678-5", razon_social="Ficticio")
        for cambios in [{"proveedor": proveedor.pk}, {"monto": "0"}, {"monto": "-1"}, {"monto": "1,5"},
                        {"monto": "1000000000"}, {"descripcion": ""}, {"fecha": ""}, {"acuerdo": ""}]:
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(reverse("gastos:fondo_egreso"), self.datos(**cambios))
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].errors)
                self.assertContains(respuesta, 'aria-invalid="true"')
        self.assertEqual(self.Movimiento.objects.count(), 2)

    def test_apertura_avisada_y_post_inicial_valido(self):
        self.client.force_login(self.e.administrador)
        self.Movimiento.objects.filter(condominio=self.e.condominio).delete()
        crear_periodo(self.e.condominio, estado="EMITIDO")
        self.assertContains(self.client.get(reverse("gastos:fondo")), "Configura el saldo inicial")
        self.assertRedirects(self.client.post(reverse("gastos:fondo_inicial"), self.datos(fecha="2026-11-01")),
                             self.Movimiento.objects.latest("pk").get_absolute_url())

    def test_paginacion_y_sin_admin_edicion_borrado(self):
        from django.contrib import admin
        from django.urls import NoReverseMatch
        self.assertNotIn(self.Movimiento, admin.site._registry)
        for nombre in ("fondo_editar", "fondo_eliminar"):
            with self.assertRaises(NoReverseMatch):
                reverse("gastos:" + nombre, args=[self.movimiento.pk])
        self.client.force_login(self.e.comite)
        self.Movimiento.objects.bulk_create([self.Movimiento(condominio=self.e.condominio, tipo="AJUSTE", monto=1,
            fecha=date(2026, 10, 2), descripcion="Ficticio", acuerdo="Acta") for _ in range(26)])
        respuesta = self.client.get(reverse("gastos:fondo"))
        self.assertTrue(respuesta.context["is_paginated"])
        self.assertEqual(len(respuesta.context["movimientos"]), 25)

    def test_permisos_emision_y_periodo_ajeno_sin_efectos(self):
        from apps.auditoria.models import RegistroAuditoria
        periodo = crear_periodo(self.e.condominio)
        ajeno = crear_periodo(self.e.ajeno)
        previos = RegistroAuditoria.objects.count()
        for usuario in (self.e.comite, self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(periodo.get_absolute_url()).status_code, 200 if usuario == self.e.comite else 403)
            ruta = reverse("gastos:periodo_emitir", args=[periodo.pk])
            self.assertEqual(self.client.get(ruta).status_code, 403)
            self.assertEqual(self.client.post(ruta).status_code, 403)
        self.client.force_login(self.e.administrador)
        ruta = reverse("gastos:periodo_emitir", args=[ajeno.pk])
        self.assertEqual(self.client.get(ruta).status_code, 404)
        self.assertEqual(self.client.post(ruta).status_code, 404)
        self.assertFalse(DetalleGastoComun.objects.exists())
        self.assertEqual(RegistroAuditoria.objects.count(), previos)


@skipUnlessDBFeature("has_select_for_update")
class FondoConcurrenciaTest(TransactionTestCase):
    """Dos conexiones y transacciones reales: deben serializar por condominio en MySQL."""

    def setUp(self):
        self.e = crear_escenario()

    def competir(self, operacion):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        barrera = Barrier(2)
        def ejecutar():
            try:
                barrera.wait(timeout=10)
                operacion()
                return "creado"
            except ValidationError:
                return "rechazado"
            finally:
                connections.close_all()
        self.assertEqual(connection.vendor, "mysql")
        with ThreadPoolExecutor(max_workers=2) as hilos:
            resultados = [hilos.submit(ejecutar) for _ in range(2)]
            self.assertCountEqual([r.result(timeout=30) for r in resultados], ["creado", "rechazado"])

    def test_dos_aperturas_simultaneas(self):
        from .fondo import registrar_movimiento
        from .models import MovimientoFondo
        from apps.auditoria.models import RegistroAuditoria
        self.competir(lambda: registrar_movimiento(self.e.condominio, tipo="INICIAL", monto=0,
            fecha=date(2026, 10, 1), descripcion="Respaldo ficticio"))
        self.assertEqual(MovimientoFondo.objects.count(), 1)
        self.assertEqual(RegistroAuditoria.objects.filter(objeto_tipo="movimientofondo").count(), 1)

    def test_dos_emisiones_simultaneas(self):
        from .servicios import emitir_periodo
        from .models import MovimientoFondo
        from apps.auditoria.models import RegistroAuditoria
        periodo = crear_periodo(self.e.condominio)
        crear_egreso(periodo, self.e.administrador)
        self.competir(lambda: emitir_periodo(periodo))
        self.assertEqual(DetalleGastoComun.objects.count(), 3)
        self.assertEqual(MovimientoFondo.objects.count(), 1)
        self.assertEqual(RegistroAuditoria.objects.filter(objeto_tipo="periodogasto").count(), 1)
        self.assertEqual(RegistroAuditoria.objects.filter(objeto_tipo="movimientofondo").count(), 1)

    def test_orden_bloqueos_condominio_antes_del_periodo(self):
        from django.test.utils import CaptureQueriesContext
        from .servicios import emitir_periodo
        periodo = crear_periodo(self.e.condominio)
        crear_egreso(periodo, self.e.administrador)
        with CaptureQueriesContext(connection) as consultas:
            emitir_periodo(periodo)
        bloqueos = [q["sql"] for q in consultas if "FOR UPDATE" in q["sql"]]
        self.assertIn("condominios_condominio", bloqueos[0])
        self.assertIn("gastos_periodogasto", bloqueos[1])


class FondoMigracionTest(TransactionTestCase):
    def tearDown(self):
        call_command("migrate", verbosity=0)

    def test_migracion_conserva_cobros_sin_ingresos_retroactivos(self):
        antes = [("gastos", "0006_vencimiento_y_reglamento")]
        despues = [("gastos", "0007_movimiento_fondo")]
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(antes)
        estado = ejecutor.loader.project_state(antes).apps
        condominio = estado.get_model("condominios", "Condominio").objects.create(nombre="Legado ficticio")
        edificio = estado.get_model("condominios", "Edificio").objects.create(condominio=condominio, nombre="A")
        unidad = estado.get_model("condominios", "Unidad").objects.create(edificio=edificio, numero="1", alicuota=1)
        periodo = estado.get_model("gastos", "PeriodoGasto").objects.create(condominio=condominio, anio=2026, mes=10,
            estado="EMITIDO", fecha_vencimiento=date(2026, 11, 10))
        cobro = estado.get_model("gastos", "DetalleGastoComun").objects.create(periodo=periodo, unidad=unidad,
            monto=100, monto_fondo_reserva=5)
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(despues)
        nuevo = ejecutor.loader.project_state(despues).apps
        self.assertEqual(nuevo.get_model("gastos", "DetalleGastoComun").objects.get(pk=cobro.pk).monto_fondo_reserva, 5)
        self.assertFalse(nuevo.get_model("gastos", "MovimientoFondo").objects.exists())
