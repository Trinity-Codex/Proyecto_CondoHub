"""
Pruebas de la evolución del fondo de reserva (RQ-05, #119).

Escenario ficticio (crear_escenario: Torre A con A101 0,4 y A102 0,3; Torre B con B101 0,3):
  - 01-08-2026 saldo inicial $100.000
  - agosto: período emitido con egresos de $100.000 -> aporte 5 % = $5.000 (2.000 / 1.500 / 1.500)
  - septiembre: período ABIERTO (sin emitir) y un egreso del fondo de $3.000
  - octubre: período emitido con $200.000 -> aporte $10.000 (4.000 / 3.000 / 3.000), más una multa
    (ítem de cobro) a A101 que NO aporta al fondo; y un ajuste de -$500
  - noviembre: período abierto, sin movimientos
Saldos de cierre: agosto 105.000, septiembre 102.000, octubre 111.500, noviembre 111.500.
"""
from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.condominios.models import Condominio, Residente, Unidad
from apps.core.pruebas import crear_escenario, crear_usuario

from . import evolucion
from .fondo import registrar_movimiento, saldo_fondo
from .models import Egreso, ItemCobro, PeriodoGasto
from .servicios import emitir_periodo, guardar_item

HOY = date(2026, 11, 19)
CIERRES = [(2026, 8, 105000), (2026, 9, 102000), (2026, 10, 111500), (2026, 11, 111500)]


def periodo_emitido(condominio, usuario, mes, egresos, items=()):
    periodo = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=mes)
    Egreso.objects.create(periodo=periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo ficticio",
                          monto=egresos, fecha=date(2026, mes, 5), creado_por=usuario)
    for item, unidades in items:
        guardar_item(ItemCobro(periodo=periodo, creado_por=usuario, **item), unidades, usuario=usuario)
    emitir_periodo(periodo, usuario=usuario)
    return periodo


class EscenarioFondoMixin:
    def setUp(self):
        self.e = e = crear_escenario()
        registrar_movimiento(e.condominio, tipo="INICIAL", monto=100000, fecha=date(2026, 8, 1),
                             descripcion="Saldo inicial ficticio")
        self.agosto = periodo_emitido(e.condominio, e.administrador, 8, 100000)
        self.septiembre = PeriodoGasto.objects.create(condominio=e.condominio, anio=2026, mes=9)
        registrar_movimiento(e.condominio, tipo="EGRESO", monto=3000, fecha=date(2026, 9, 15),
                             descripcion="Reparación ficticia", acuerdo="Acta ficticia 1")
        multa = {"nombre": "Multa ficticia", "modo": ItemCobro.Modo.POR_UNIDAD, "monto": 25000,
                 "alcance": ItemCobro.Alcance.ALGUNAS}
        self.octubre = periodo_emitido(e.condominio, e.administrador, 10, 200000, items=[(multa, [e.a101])])
        registrar_movimiento(e.condominio, tipo="AJUSTE", monto=-500, fecha=date(2026, 10, 20),
                             descripcion="Corrección ficticia", acuerdo="Acta ficticia 2")
        self.noviembre = PeriodoGasto.objects.create(condominio=e.condominio, anio=2026, mes=11)
        # Otro condominio con su propio fondo: nunca debe aparecer en el de "Prueba".
        registrar_movimiento(e.ajeno, tipo="INICIAL", monto=999999, fecha=date(2026, 8, 1), descripcion="Fondo ajeno")
        periodo_emitido(e.ajeno, e.administrador, 8, 777000)


class SerieMensualTest(EscenarioFondoMixin, TestCase):
    def test_cada_cierre_cuadra_con_saldo_fondo_y_con_sus_movimientos(self):
        serie = evolucion.serie_mensual(self.e.condominio, hoy=HOY)
        self.assertEqual([(f.anio, f.mes, f.cierre) for f in serie], CIERRES)
        periodos = [self.agosto, self.septiembre, self.octubre, self.noviembre]
        for fila, periodo in zip(serie, periodos):
            with self.subTest(mes=fila.mes):
                self.assertEqual(fila.cierre, saldo_fondo(self.e.condominio, periodo))
                self.assertEqual(fila.apertura + fila.aportes - fila.egresos + fila.ajustes, fila.cierre)
        for anterior, siguiente in zip(serie, serie[1:]):
            self.assertEqual(anterior.cierre, siguiente.apertura)
        self.assertEqual(serie[-1].cierre, saldo_fondo(self.e.condominio))

    def test_columnas_del_mes_y_meses_sin_emision_sin_aporte_inventado(self):
        agosto, septiembre, octubre, noviembre = evolucion.serie_mensual(self.e.condominio, hoy=HOY)
        self.assertEqual((agosto.apertura, agosto.aportes, agosto.emitido), (100000, 5000, True))
        self.assertEqual((septiembre.aportes, septiembre.egresos, septiembre.emitido), (0, 3000, False))
        self.assertEqual((octubre.aportes, octubre.ajustes, octubre.emitido), (10000, -500, True))
        self.assertEqual((noviembre.aportes, noviembre.egresos, noviembre.emitido), (0, 0, False))

    def test_los_items_de_cobro_no_aportan_al_fondo(self):
        cobro = self.octubre.detalles.get(unidad=self.e.a101)
        self.assertEqual((cobro.monto_items, cobro.monto_fondo_reserva), (25000, 4000))
        self.assertEqual(evolucion.serie_mensual(self.e.condominio, hoy=HOY)[2].aportes, 10000)
        unidades = {f["unidad"]: f["aporte"] for f in evolucion.por_unidad(self.e.condominio)["unidades"]}
        self.assertEqual(unidades[self.e.a101], 6000)

    def test_fondo_sin_movimientos_y_sin_apertura(self):
        vacio = Condominio.objects.create(nombre="Vacío", direccion="Calle 3", comuna="Santiago")
        self.assertEqual(evolucion.serie_mensual(vacio), [])
        sin_apertura = Condominio.objects.create(nombre="Legado", direccion="Calle 4", comuna="Santiago")
        PeriodoGasto.objects.create(condominio=sin_apertura, anio=2026, mes=7, estado=PeriodoGasto.Estado.EMITIDO)
        with self.assertRaisesMessage(ValidationError, "Configura el saldo inicial"):
            evolucion.serie_mensual(sin_apertura)

    def test_grafico_usa_los_mismos_cierres_y_soporta_negativos(self):
        serie = evolucion.serie_mensual(self.e.condominio, hoy=HOY)
        grafico = evolucion.grafico(serie)
        self.assertEqual([b["fila"].cierre for b in grafico["barras"]], [f.cierre for f in serie])
        self.assertEqual(len(grafico["barras"]), len(serie))
        negativa = evolucion.grafico([evolucion.MesFondo(2026, 1, cierre=-100), evolucion.MesFondo(2026, 2, cierre=300)])
        baja, alta = negativa["barras"]
        self.assertEqual(baja["y"], negativa["cero"])
        self.assertAlmostEqual(alta["y"] + alta["alto"], negativa["cero"])
        self.assertIsNone(evolucion.grafico([]))


class PorEdificioYUnidadTest(EscenarioFondoMixin, TestCase):
    def test_aportes_por_mes_y_saldo_por_edificio_suman_el_total(self):
        datos = evolucion.por_edificio(self.e.condominio, evolucion.serie_mensual(self.e.condominio, hoy=HOY))
        self.assertEqual([e.nombre for e in datos["edificios"]], ["Torre A", "Torre B"])
        self.assertEqual([(m.mes, montos, total) for m, montos, total in datos["meses"]],
                         [(8, [3500, 1500], 5000), (10, [7000, 3000], 10000)])
        # Lo que no es aporte (100.000 - 3.000 - 500 = 96.500) se reparte 0,7 / 0,3.
        self.assertEqual([(f["aporte"], f["parte"], f["saldo"]) for f in datos["filas"]],
                         [(10500, 67550, 78050), (4500, 28950, 33450)])
        self.assertEqual(sum(f["saldo"] for f in datos["filas"]), saldo_fondo(self.e.condominio))

    def test_reparto_negativo_y_sin_alicuotas(self):
        registrar_movimiento(self.e.condominio, tipo="EGRESO", monto=200001, fecha=date(2026, 11, 2),
                             descripcion="Egreso ficticio grande", acuerdo="Acta ficticia 3")
        datos = evolucion.por_edificio(self.e.condominio, evolucion.serie_mensual(self.e.condominio, hoy=HOY))
        self.assertEqual(sum(f["saldo"] for f in datos["filas"]), saldo_fondo(self.e.condominio))
        self.assertLess(datos["filas"][0]["parte"], 0)
        Unidad.objects.filter(edificio__condominio=self.e.condominio).update(alicuota=0)
        datos = evolucion.por_edificio(self.e.condominio, evolucion.serie_mensual(self.e.condominio, hoy=HOY))
        self.assertTrue(datos["sin_alicuotas"])
        self.assertIsNone(datos["filas"][0]["saldo"])

    def test_aporte_por_unidad_y_por_residente_segun_fechas_de_residencia(self):
        anterior = crear_usuario("anterior@prueba.cl")
        nuevo = crear_usuario("nuevo@prueba.cl")
        Residente.objects.create(usuario=anterior, unidad=self.e.a102, desde=date(2020, 1, 1),
                                 activo=False, hasta=date(2026, 8, 31))
        Residente.objects.create(usuario=nuevo, unidad=self.e.a102, desde=date(2026, 10, 5))
        datos = evolucion.por_unidad(self.e.condominio)
        self.assertEqual([(f["unidad"].numero, f["aporte"]) for f in datos["unidades"]],
                         [("A101", 6000), ("A102", 4500), ("B101", 4500)])
        self.assertEqual(datos["total"], 15000)
        residentes = {f["residencia"].usuario: f["aporte"] for f in datos["residentes"]}
        # La residencia dada de baja no se lista; la nueva solo suma desde octubre.
        self.assertEqual(residentes, {self.e.residente: 6000, nuevo: 3000, self.e.residente_b: 4500})
        self.assertNotIn(anterior, residentes)


@mock.patch("apps.gastos.evolucion.timezone.localdate", return_value=HOY)
class VistasEvolucionTest(EscenarioFondoMixin, TestCase):
    def test_administrador_y_comite_ven_evolucion_edificios_y_unidades(self, _hoy):
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario):
                respuesta = self.client.get(reverse("gastos:fondo_evolucion"))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual([f.cierre for f in respuesta.context["serie"]], [c for _, _, c in CIERRES])
                self.assertContains(respuesta, "Sin período emitido", count=2)
                self.assertContains(respuesta, "<svg", count=1)
                self.assertContains(respuesta, "Octubre 2026: $111.500")  # título de la barra = cierre de la tabla
                self.assertContains(respuesta, "$78.050")
                self.assertContains(respuesta, reverse("gastos:fondo_unidad", args=[self.e.b101.pk]))
                self.assertNotContains(respuesta, "Torre única")
                self.assertNotContains(respuesta, "$999.999")

    def test_residente_y_conserje_sin_acceso_a_evolucion(self, _hoy):
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("gastos:fondo_evolucion")).status_code, 403)

    def test_desglose_de_unidad_por_rol(self, _hoy):
        casos = [
            (self.e.administrador, self.e.b101, 200), (self.e.comite, self.e.a101, 200),
            (self.e.residente, self.e.a101, 200), (self.e.residente, self.e.b101, 403),
            (self.e.residente, self.e.a102, 403), (self.e.conserje, self.e.a101, 403),
            (self.e.administrador, self.e.unidad_ajena, 404), (self.e.comite, self.e.unidad_ajena, 404),
            (self.e.residente, self.e.unidad_ajena, 404),
        ]
        for usuario, unidad, esperado in casos:
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario, unidad=unidad):
                respuesta = self.client.get(reverse("gastos:fondo_unidad", args=[unidad.pk]))
                self.assertEqual(respuesta.status_code, esperado)
                if esperado != 200:
                    self.assertNotIn("cobros", respuesta.context or {})

    def test_residente_ve_saldo_total_y_solo_su_aporte(self, _hoy):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("gastos:fondo_mi_aporte"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual((respuesta.context["saldo"], respuesta.context["total"]), (111500, 6000))
        self.assertEqual([u["unidad"] for u in respuesta.context["unidades"]], [self.e.a101])
        self.assertNotContains(respuesta, "B101")
        self.assertNotContains(respuesta, "Torre B")
        respuesta = self.client.get(reverse("gastos:fondo_unidad", args=[self.e.a101.pk]))
        self.assertEqual(respuesta.context["total"], 6000)

    def test_residente_recien_llegado_ve_solo_meses_de_su_residencia(self, _hoy):
        nuevo = crear_usuario("nuevo@prueba.cl")
        Residente.objects.create(usuario=nuevo, unidad=self.e.a102, desde=date(2026, 10, 5))
        self.client.force_login(nuevo)
        respuesta = self.client.get(reverse("gastos:fondo_mi_aporte"))
        self.assertEqual(respuesta.context["total"], 3000)
        self.assertEqual([c.periodo for c in respuesta.context["unidades"][0]["cobros"]], [self.octubre])
        respuesta = self.client.get(reverse("gastos:fondo_unidad", args=[self.e.a102.pk]))
        self.assertEqual(respuesta.context["total"], 3000)

    def test_conserje_sin_vista_del_residente(self, _hoy):
        self.client.force_login(self.e.conserje)
        self.assertEqual(self.client.get(reverse("gastos:fondo_mi_aporte")).status_code, 403)

    def test_sin_apertura_avisa_y_no_inventa_saldo(self, _hoy):
        from apps.gastos.models import MovimientoFondo
        MovimientoFondo.objects.filter(condominio=self.e.condominio).delete()
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("gastos:fondo_evolucion"))
        self.assertContains(respuesta, "Configura el saldo inicial")
        self.assertNotIn("serie", respuesta.context)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("gastos:fondo_mi_aporte"))
        self.assertIsNone(respuesta.context["saldo"])
        self.assertContains(respuesta, "aún no está disponible")

    def test_enlaces_desde_el_fondo_y_el_menu_del_residente(self, _hoy):
        self.client.force_login(self.e.comite)
        self.assertContains(self.client.get(reverse("gastos:fondo")), reverse("gastos:fondo_evolucion"))
        self.client.force_login(self.e.residente)
        self.assertContains(self.client.get(reverse("core:inicio")), reverse("gastos:fondo_mi_aporte"))
