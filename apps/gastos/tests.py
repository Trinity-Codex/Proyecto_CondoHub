"""
Pruebas de gastos comunes: períodos y egresos (Issue #1, RF02).

Cada clase corresponde a un criterio de aceptación del Issue.
"""
from datetime import date

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.core.templatetags.condohub import pesos

from .models import DetalleGastoComun, Egreso, PeriodoGasto


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
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5"})
        periodo = PeriodoGasto.objects.get()
        self.assertRedirects(respuesta, periodo.get_absolute_url())
        self.assertEqual(periodo.condominio, self.e.condominio)
        self.assertTrue(periodo.esta_abierto)
        self.assertEqual(str(periodo), "Octubre 2026")

    def test_no_se_repite_el_mes(self):
        crear_periodo(self.e.condominio)
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].non_field_errors())
        self.assertEqual(PeriodoGasto.objects.count(), 1)

    def test_el_mismo_mes_en_otro_condominio_si_se_puede(self):
        crear_periodo(self.e.ajeno)
        self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "5"})
        self.assertEqual(PeriodoGasto.objects.filter(condominio=self.e.condominio).count(), 1)

    def test_fondo_de_reserva_minimo_5(self):
        respuesta = self.client.post(reverse("gastos:periodo_nuevo"), {"mes": 10, "anio": 2026, "porcentaje_fondo_reserva": "4"})
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
        for monto in ["0", "-500", "1500.5", "abc", "1000000000"]:
            respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[self.periodo.pk]), self.datos(monto=monto))
            self.assertIn("monto", respuesta.context["form"].errors, monto)
        self.assertFalse(Egreso.objects.exists())


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


class FiltroPesosTest(SimpleTestCase):
    def test_formato_chileno(self):
        self.assertEqual(pesos(1234567), "$1.234.567")
        self.assertEqual(pesos(990), "$990")
        self.assertEqual(pesos(None), "$0")
        self.assertEqual(pesos(-5000), "-$5.000")
