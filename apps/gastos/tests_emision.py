"""
Pruebas del cálculo y la emisión de gastos comunes (Issue #2, RF02).

Cada clase corresponde a un criterio de aceptación del Issue:
  - la suma de las unidades es exactamente el total (redondeo sin perder pesos)
  - no se emite si las alícuotas no suman 1
  - no se emite dos veces el mismo período
  - el fondo de reserva nunca es menor al 5 %
  - cambiar de estrategia no requiere tocar la vista ni el modelo
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.condominios.models import Unidad
from apps.core.pruebas import crear_escenario
from apps.notificaciones.models import Notificacion

from .models import DetalleGastoComun, Egreso, PeriodoGasto
from .prorrateo import ESTRATEGIAS, PartesIguales, PorAlicuota, repartir
from .servicios import calcular_emision, emitir_periodo


@dataclass(frozen=True)  # frozen: inmutable y "hasheable", así sirve como clave de diccionario
class UnidadFalsa:
    """Unidad de mentira para probar el prorrateo sin base de datos."""

    pk: int
    alicuota: Decimal


def unidad_falsa(pk, alicuota):
    return UnidadFalsa(pk=pk, alicuota=Decimal(alicuota))


class RepartirTest(SimpleTestCase):
    """Criterio: la suma de todas las unidades es exactamente el total."""

    def test_reparto_exacto(self):
        a, b = unidad_falsa(1, "0.5"), unidad_falsa(2, "0.5")
        self.assertEqual(repartir(1000, {a: 1, b: 1}), {a: 500, b: 500})

    def test_los_pesos_sobrantes_no_se_pierden(self):
        # $100 entre 3 iguales: 33,33 cada una -> el peso que sobra va a una sola.
        unidades = [unidad_falsa(i, "1") for i in (1, 2, 3)]
        montos = repartir(100, {u: Decimal("1") for u in unidades})
        self.assertEqual(sum(montos.values()), 100)
        self.assertEqual(sorted(montos.values()), [33, 33, 34])

    def test_el_sobrante_va_a_la_mayor_parte_decimal(self):
        # 1000 × (0.333 / 0.333 / 0.334): exactos 333,0 / 333,0 / 334,0 -> sin sobrantes
        # 1001: exactos 333,333 / 333,333 / 334,334 -> sobra 1 peso y va a la de 0,334
        a, b, c = unidad_falsa(1, "0.333"), unidad_falsa(2, "0.333"), unidad_falsa(3, "0.334")
        montos = repartir(1001, {a: a.alicuota, b: b.alicuota, c: c.alicuota})
        self.assertEqual(montos, {a: 333, b: 333, c: 335})

    def test_siempre_suma_el_total(self):
        alicuotas = ["0.123457", "0.234568", "0.345679", "0.296296"]  # suman 1
        unidades = [unidad_falsa(i, a) for i, a in enumerate(alicuotas, start=1)]
        for total in [1, 7, 999, 123457, 2166200, 987654321]:
            montos = PorAlicuota().calcular(total, unidades)
            self.assertEqual(sum(montos.values()), total, total)

    def test_resultado_siempre_igual(self):
        """Con empates, el resultado no depende del azar (desempata el id de la unidad)."""
        unidades = [unidad_falsa(i, "1") for i in (3, 1, 2)]
        primero = repartir(10, {u: Decimal("1") for u in unidades})
        for _ in range(5):
            self.assertEqual(repartir(10, {u: Decimal("1") for u in reversed(unidades)}), primero)

    def test_total_cero(self):
        a = unidad_falsa(1, "1")
        self.assertEqual(repartir(0, {a: 1}), {a: 0})


class EstrategiasTest(SimpleTestCase):
    """Criterio: cambiar de estrategia no requiere modificar la vista ni el modelo."""

    def test_por_alicuota(self):
        a, b = unidad_falsa(1, "0.75"), unidad_falsa(2, "0.25")
        self.assertEqual(PorAlicuota().calcular(1000, [a, b]), {a: 750, b: 250})

    def test_partes_iguales_ignora_la_alicuota(self):
        a, b = unidad_falsa(1, "0.75"), unidad_falsa(2, "0.25")
        self.assertEqual(PartesIguales().calcular(1000, [a, b]), {a: 500, b: 500})

    def test_cada_criterio_del_modelo_tiene_su_estrategia(self):
        self.assertEqual(set(PeriodoGasto.Criterio.values), set(ESTRATEGIAS))


class EmisionTest(TestCase):
    """Emisión completa sobre la base de datos (escenario: A101 0,4 · A102 0,3 · B101 0,3)."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10)
        Egreso.objects.create(
            periodo=self.periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo",
            monto=1000001, fecha=date(2026, 10, 1), creado_por=self.e.administrador,
        )

    def test_crea_un_cobro_por_unidad_y_cuadra(self):
        emitir_periodo(self.periodo)
        cobros = DetalleGastoComun.objects.filter(periodo=self.periodo)
        self.assertEqual(cobros.count(), 3)
        self.assertEqual(sum(c.monto for c in cobros), 1000001)        # total exacto de egresos
        self.assertEqual(sum(c.monto_fondo_reserva for c in cobros), 50000)  # 5 % redondeado
        self.assertEqual(cobros.get(unidad=self.e.a101).monto, 400001)  # 40 % + el peso sobrante

    def test_cierra_el_periodo(self):
        emitir_periodo(self.periodo)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, PeriodoGasto.Estado.EMITIDO)
        self.assertIsNotNone(self.periodo.fecha_emision)

    def test_avisa_a_los_residentes(self):
        emitir_periodo(self.periodo)
        avisados = set(Notificacion.objects.filter(titulo="Gastos comunes emitidos").values_list("usuario__email", flat=True))
        self.assertEqual(avisados, {"residente@prueba.cl", "residente.b@prueba.cl"})

    def test_no_se_emite_dos_veces(self):
        emitir_periodo(self.periodo)
        with self.assertRaises(ValidationError):
            emitir_periodo(self.periodo)
        self.assertEqual(DetalleGastoComun.objects.count(), 3)

    def test_no_se_emite_si_las_alicuotas_no_suman_1(self):
        Unidad.objects.filter(pk=self.e.a101.pk).update(alicuota=Decimal("0.5"))  # ahora suman 1,1
        emision = calcular_emision(self.periodo)
        self.assertFalse(emision.puede_emitir)
        self.assertIn("deben sumar 1", emision.errores[0])
        with self.assertRaises(ValidationError):
            emitir_periodo(self.periodo)

    def test_partes_iguales_no_exige_alicuotas(self):
        Unidad.objects.filter(pk=self.e.a101.pk).update(alicuota=Decimal("0.5"))
        self.periodo.criterio_prorrateo = PeriodoGasto.Criterio.PARTES_IGUALES
        self.periodo.save()
        emitir_periodo(self.periodo)
        montos = sorted(DetalleGastoComun.objects.values_list("monto", flat=True))
        self.assertEqual(montos, [333333, 333334, 333334])

    def test_no_se_emite_sin_egresos(self):
        self.periodo.egresos.all().delete()
        self.assertFalse(calcular_emision(self.periodo).puede_emitir)

    def test_fondo_de_reserva_mayor(self):
        """Criterio: el fondo nunca es menor al 5 %; si la asamblea fija más, se respeta."""
        self.periodo.porcentaje_fondo_reserva = Decimal("10")
        self.periodo.save()
        self.assertEqual(calcular_emision(self.periodo).total_fondo, 100000)


class EmitirVistaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10)
        Egreso.objects.create(
            periodo=self.periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo",
            monto=300000, fecha=date(2026, 10, 1), creado_por=self.e.administrador,
        )
        self.url = reverse("gastos:periodo_emitir", args=[self.periodo.pk])

    def test_solo_el_administrador(self):
        for usuario, esperado in [(self.e.administrador, 200), (self.e.comite, 403), (self.e.residente, 403), (self.e.conserje, 403)]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url).status_code, esperado, usuario)

    def test_vista_previa_no_guarda_nada(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url)
        self.assertEqual(len(respuesta.context["emision"].filas), 3)
        self.assertContains(respuesta, "$120.000")  # A101: 40 % de $300.000
        self.assertFalse(DetalleGastoComun.objects.exists())

    def test_emitir_desde_la_vista(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(self.url)
        self.assertRedirects(respuesta, self.periodo.get_absolute_url())
        self.assertEqual(DetalleGastoComun.objects.count(), 3)
        detalle = self.client.get(self.periodo.get_absolute_url())
        self.assertEqual(len(detalle.context["cobros"]), 3)

    def test_error_se_muestra_y_no_emite(self):
        Unidad.objects.filter(pk=self.e.a101.pk).update(alicuota=Decimal("0.9"))
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(self.url, follow=True)
        self.assertContains(respuesta, "deben sumar 1")
        self.assertFalse(DetalleGastoComun.objects.exists())

    def test_periodo_de_otro_condominio(self):
        ajeno = PeriodoGasto.objects.create(condominio=self.e.ajeno, anio=2026, mes=10)
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.post(reverse("gastos:periodo_emitir", args=[ajeno.pk])).status_code, 404)
