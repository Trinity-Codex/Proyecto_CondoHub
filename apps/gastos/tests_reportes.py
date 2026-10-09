"""
Pruebas del reporte de gastos comunes y morosidad (Issue #5, RF11).

Criterios de aceptación del Issue:
  - visible para administrador y comité
  - los totales cuadran con los cobros (y con lo emitido en el Issue #2)
  - el CSV se abre bien en Excel (";" y UTF-8 con BOM)
  - pruebas de los cálculos (incluidos los pagos parciales del Issue #4)

Escenario de las pruebas (cada cobro es de $42.000: 40.000 de gastos + 2.000 de fondo):

    período       A101 (Torre A)   A102 (Torre A)   B101 (Torre B)
    agosto        pagado           PENDIENTE        pagado
    septiembre    pagado           PENDIENTE        PENDIENTE
    octubre       PENDIENTE        PENDIENTE        PENDIENTE
    noviembre     (abierto: sin cobros)

En el reporte de SEPTIEMBRE: A101 está al día, B101 debe solo septiembre
(pendiente) y A102 arrastra agosto (morosa). Octubre es POSTERIOR: no cuenta.
"""
from datetime import date

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.pagos.consultas import cobros_del_residente, con_saldos, total_adeudado
from apps.pagos.models import Pago

from .models import DetalleGastoComun, Egreso, PeriodoGasto
from .reportes import anotar_pagado, generar_reporte
from .servicios import emitir_periodo
from .views import celda_segura

PAGADO = DetalleGastoComun.Estado.PAGADO
PENDIENTE = DetalleGastoComun.Estado.PENDIENTE
MOROSO = DetalleGastoComun.Estado.MOROSO
EMITIDO = PeriodoGasto.Estado.EMITIDO


class EscenarioReporte(TestCase):
    """Datos comunes a las pruebas del reporte (ver la tabla del comienzo del archivo)."""

    def setUp(self):
        self.e = crear_escenario()
        condominio = self.e.condominio
        self.ago = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=8, estado=EMITIDO)
        self.sep = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=9, estado=EMITIDO)
        self.oct = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=10, estado=EMITIDO)
        self.nov = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=11)
        a101, a102, b101 = self.e.a101, self.e.a102, self.e.b101
        for periodo, estados in (
            (self.ago, (PAGADO, PENDIENTE, PAGADO)),
            (self.sep, (PAGADO, PENDIENTE, PENDIENTE)),
            (self.oct, (PENDIENTE, PENDIENTE, PENDIENTE)),
        ):
            for unidad, estado in zip((a101, a102, b101), estados):
                DetalleGastoComun.objects.create(
                    periodo=periodo, unidad=unidad, monto=40000, monto_fondo_reserva=2000, estado=estado
                )

    def fila_de(self, reporte, unidad):
        return next(f for f in reporte.filas if f.unidad == unidad)


class CalculosTest(EscenarioReporte):
    """Criterio: pruebas de los cálculos."""

    def test_totales_del_periodo(self):
        r = generar_reporte(self.sep)
        self.assertEqual(r.total_emitido, 126000)     # 3 × 42.000
        self.assertEqual(r.total_recaudado, 42000)    # solo A101
        self.assertEqual(r.saldo_periodo, 84000)
        self.assertEqual(r.porcentaje_recaudacion, 33.3)

    def test_unidad_que_arrastra_deuda_es_morosa(self):
        a102 = self.fila_de(generar_reporte(self.sep), self.e.a102)
        self.assertEqual(a102.deuda_anterior, 42000)  # agosto
        self.assertEqual(a102.deuda_total, 84000)     # agosto + septiembre
        self.assertTrue(a102.es_morosa)
        self.assertEqual(a102.situacion, "Morosa")

    def test_deber_solo_el_mes_del_reporte_no_es_morosidad(self):
        b101 = self.fila_de(generar_reporte(self.sep), self.e.b101)
        self.assertEqual(b101.saldo, 42000)
        self.assertFalse(b101.es_morosa)
        self.assertEqual(b101.situacion, "Pendiente")

    def test_unidad_al_dia(self):
        a101 = self.fila_de(generar_reporte(self.sep), self.e.a101)
        self.assertEqual((a101.saldo, a101.deuda_total, a101.situacion), (0, 0, "Al día"))

    def test_los_periodos_posteriores_no_cuentan(self):
        # Octubre está impago para todos, pero es posterior a septiembre.
        r = generar_reporte(self.sep)
        self.assertEqual(r.deuda_anterior, 42000)     # solo agosto de A102
        self.assertEqual(len(r.unidades_morosas), 1)

    def test_en_octubre_se_acumula_la_deuda(self):
        r = generar_reporte(self.oct)
        a102 = self.fila_de(r, self.e.a102)
        self.assertEqual(a102.deuda_anterior, 84000)  # agosto + septiembre
        self.assertEqual(len(r.unidades_morosas), 2)  # A102 y B101 (debe septiembre)

    def test_filtro_por_edificio(self):
        r = generar_reporte(self.sep, edificio=self.e.torre_b)
        self.assertEqual([f.unidad for f in r.filas], [self.e.b101])
        self.assertEqual(r.total_emitido, 42000)
        self.assertEqual(r.deuda_anterior, 0)         # la deuda de A102 es de la Torre A

    def test_un_cobro_moroso_cuenta_como_impago(self):
        cobro = self.sep.detalles.get(unidad=self.e.a102)
        cobro.estado = MOROSO
        cobro.save()
        anotado = anotar_pagado(DetalleGastoComun.objects.filter(pk=cobro.pk)).get()
        self.assertEqual((anotado.total_cobro, anotado.pagado), (42000, 0))

    def test_sin_cobros_el_porcentaje_es_cero(self):
        self.assertEqual(generar_reporte(self.nov).porcentaje_recaudacion, 0)


class PagosParcialesTest(EscenarioReporte):
    """Con el modelo Pago (Issue #4) el reporte cuenta los abonos parciales."""

    def cobro(self, periodo, unidad):
        return periodo.detalles.get(unidad=unidad)

    def test_un_abono_parcial_se_cuenta_como_recaudado(self):
        Pago.registrar(self.cobro(self.sep, self.e.b101), monto=10000)
        r = generar_reporte(self.sep)
        b101 = self.fila_de(r, self.e.b101)
        self.assertEqual((b101.pagado, b101.saldo, b101.situacion), (10000, 32000, "Pendiente"))
        self.assertEqual(r.total_recaudado, 52000)   # 42.000 de A101 + el abono

    def test_pagar_el_mes_no_borra_la_deuda_anterior(self):
        # A102 paga septiembre completo, pero sigue debiendo agosto: sigue morosa.
        Pago.registrar(self.cobro(self.sep, self.e.a102), monto=42000)
        a102 = self.fila_de(generar_reporte(self.sep), self.e.a102)
        self.assertEqual((a102.saldo, a102.deuda_anterior), (0, 42000))
        self.assertTrue(a102.es_morosa)

    def test_el_reporte_cuadra_con_el_estado_de_cuenta_del_residente(self):
        # El residente vive en A101: debe octubre (42.000) y abona 15.000.
        Pago.registrar(self.cobro(self.oct, self.e.a101), monto=15000)
        a101 = self.fila_de(generar_reporte(self.oct), self.e.a101)
        cuenta = con_saldos(cobros_del_residente(self.e.residente, self.e.condominio))
        self.assertEqual(a101.deuda_total, total_adeudado(cuenta))
        self.assertEqual(a101.deuda_total, 27000)


class CuadraConLaEmisionTest(TestCase):
    """Criterio: los totales cuadran con lo que se emitió (Issue #2)."""

    def test_total_emitido_igual_al_total_a_cobrar(self):
        e = crear_escenario()
        periodo = PeriodoGasto.objects.create(condominio=e.condominio, anio=2026, mes=10)
        Egreso.objects.create(
            periodo=periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo", monto=1000001,
            fecha=date(2026, 10, 5), creado_por=e.administrador,
        )
        emision = emitir_periodo(periodo)
        r = generar_reporte(periodo)
        self.assertEqual(r.total_emitido, emision.total_a_cobrar)
        self.assertEqual(r.total_recaudado, 0)
        self.assertEqual(len(r.unidades_con_deuda), 3)


class VistaReporteTest(EscenarioReporte):
    """Criterio: visible para administrador y comité; filtros por período y edificio."""

    url = reverse("gastos:reporte")

    def test_administrador_y_comite_entran(self):
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_residente_y_conserje_no_entran(self):
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.get(reverse("gastos:reporte_csv")).status_code, 403)

    def test_por_defecto_muestra_el_ultimo_periodo_emitido(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["reporte"].periodo, self.oct)  # noviembre está abierto

    def test_un_periodo_abierto_no_se_puede_elegir(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"periodo": self.nov.pk})
        self.assertIsNone(respuesta.context["reporte"])
        self.assertTrue(respuesta.context["form"].errors)

    def test_no_se_ve_el_periodo_de_otro_condominio(self):
        ajeno = PeriodoGasto.objects.create(condominio=self.e.ajeno, anio=2026, mes=9, estado=EMITIDO)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"periodo": ajeno.pk})
        self.assertIsNone(respuesta.context["reporte"])

    def test_filtros_por_periodo_edificio_y_solo_deuda(self):
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(self.url, {"periodo": self.sep.pk, "edificio": self.e.torre_a.pk, "solo_deuda": "on"})
        self.assertEqual([f.unidad for f in respuesta.context["filas"]], [self.e.a102])  # A101 está al día
        # Los totales siguen siendo de toda la Torre A (A101 y A102).
        self.assertEqual(respuesta.context["reporte"].total_emitido, 84000)
        self.assertContains(respuesta, "Morosa")

    def test_la_lista_de_periodos_enlaza_el_reporte(self):
        self.client.force_login(self.e.comite)
        self.assertContains(self.client.get(reverse("gastos:periodos")), self.url)


class SinPeriodosEmitidosTest(TestCase):
    def test_mensaje_y_csv_sin_datos(self):
        e = crear_escenario()
        self.client.force_login(e.administrador)
        self.assertContains(self.client.get(reverse("gastos:reporte")), "Todavía no hay períodos emitidos")
        self.assertRedirects(self.client.get(reverse("gastos:reporte_csv")), reverse("gastos:reporte") + "?")


class CsvTest(EscenarioReporte):
    """Criterio: el CSV se abre bien en Excel (separador ";" y UTF-8 con BOM)."""

    def descargar(self, **filtros):
        self.client.force_login(self.e.administrador)
        return self.client.get(reverse("gastos:reporte_csv"), {"periodo": self.sep.pk, **filtros})

    def test_formato_para_excel(self):
        respuesta = self.descargar()
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="morosidad-2026-09.csv"', respuesta["Content-Disposition"])
        contenido = respuesta.content.decode("utf-8")
        self.assertTrue(contenido.startswith("\ufeff"))  # BOM
        encabezado = contenido.lstrip("\ufeff").splitlines()[0]
        self.assertTrue(encabezado.startswith("Edificio;Unidad;Período;Total cobrado"))

    def test_una_linea_por_unidad_y_el_total(self):
        lineas = self.descargar().content.decode("utf-8").splitlines()
        self.assertEqual(len(lineas), 1 + 3 + 1)  # encabezado + 3 unidades + total
        self.assertIn("Torre A;A102;Septiembre 2026;42000;0;42000;42000;84000;Morosa", lineas)
        self.assertEqual(lineas[-1], "Total;;Septiembre 2026;126000;42000;84000;42000;126000;33,3 % recaudado")

    def test_con_solo_deuda_el_total_aclara_que_es_de_todas(self):
        lineas = self.descargar(solo_deuda="on").content.decode("utf-8").splitlines()
        self.assertEqual(len(lineas), 1 + 2 + 1)  # A101 está al día: no aparece
        self.assertTrue(lineas[-1].startswith("Total (todas las unidades);;"))

    def test_respeta_los_filtros(self):
        lineas = self.descargar(edificio=self.e.torre_b.pk).content.decode("utf-8").splitlines()
        self.assertEqual(len(lineas), 1 + 1 + 1)
        self.assertIn("Torre B;B101", lineas[1])


class CeldaSeguraTest(SimpleTestCase):
    def test_los_textos_que_parecen_formulas_se_neutralizan(self):
        self.assertEqual(celda_segura("=HYPERLINK(\"x\")"), "'=HYPERLINK(\"x\")")
        self.assertEqual(celda_segura("Torre A"), "Torre A")
        self.assertEqual(celda_segura(-5), -5)  # los números no se tocan
