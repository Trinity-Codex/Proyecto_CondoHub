"""
Pruebas de los ítems de cobro (RQ-02, #117).

Cada clase corresponde a un criterio de aceptación del Issue:
  - un ítem aparece en el cobro del mes que corresponde y solo a las unidades alcanzadas
  - los dos modos de monto calculan bien y la suma cuadra con el total y con el reporte
  - solo el administrador usa el mantenedor (403 al resto, 404 a otro condominio) y
    un período emitido no admite cambios
  - cada alta, cambio y baja queda en la auditoría
  - el residente ve solo lo suyo (filtro de residencia #46) y la emisión resiste la concurrencia
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import RestrictedError
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Residente, Unidad
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.pagos.consultas import cobros_del_residente, total_adeudado

from .models import MONTO_MAXIMO, DetalleGastoComun, Egreso, ItemCobro, LineaCobro, PeriodoGasto
from .reportes import generar_reporte
from .servicios import calcular_emision, eliminar_item, emitir_periodo, guardar_item

TODAS, ALGUNAS = ItemCobro.Alcance.TODAS, ItemCobro.Alcance.ALGUNAS
POR_UNIDAD, PRORRATEO = ItemCobro.Modo.POR_UNIDAD, ItemCobro.Modo.PRORRATEO


def periodo_con_egreso(condominio, usuario, monto=100000, mes=10):
    periodo = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=mes)
    Egreso.objects.create(periodo=periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo", monto=monto,
                          fecha=date(2026, mes, 5), creado_por=usuario)
    return periodo


def crear_item(periodo, usuario, *, monto, modo=POR_UNIDAD, unidades=(), nombre="Ítem"):
    alcance = ALGUNAS if unidades else TODAS
    item = ItemCobro(periodo=periodo, nombre=nombre, modo=modo, monto=monto, alcance=alcance, creado_por=usuario)
    return guardar_item(item, list(unidades), usuario=usuario)


class Base(TestCase):
    def setUp(self):
        self.e = crear_escenario()  # A101 (0,4), A102 (0,3), B101 (0,3)
        self.periodo = periodo_con_egreso(self.e.condominio, self.e.administrador)

    def cobro(self, unidad):
        return DetalleGastoComun.objects.get(periodo=self.periodo, unidad=unidad)


class ModosDeMontoTest(Base):
    """Criterio: los dos modos calculan bien y la suma cuadra con el total cobrado."""

    def filas(self):
        return {fila.unidad: fila for fila in calcular_emision(self.periodo).filas}

    def test_por_unidad_dirigido_solo_a_esa_unidad(self):
        crear_item(self.periodo, self.e.administrador, monto=25000, unidades=[self.e.a101])
        filas = self.filas()
        self.assertEqual(filas[self.e.a101].items, 25000)
        self.assertEqual(filas[self.e.a102].items, 0)
        self.assertEqual(filas[self.e.b101].items, 0)

    def test_por_unidad_general_lo_paga_cada_unidad(self):
        crear_item(self.periodo, self.e.administrador, monto=10000)
        self.assertEqual([f.items for f in self.filas().values()], [10000, 10000, 10000])

    def test_prorrateo_por_alicuota_suma_exactamente_el_total(self):
        crear_item(self.periodo, self.e.administrador, monto=1001, modo=PRORRATEO)
        filas = self.filas()
        # 1001 × 0,4 / 0,3 / 0,3 = 400,4 / 300,3 / 300,3 -> 400 + 300 + 300 y el peso sobrante va a A101 (desempate).
        self.assertEqual(sum(f.items for f in filas.values()), 1001)
        self.assertEqual(filas[self.e.a101].items, 401)

    def test_prorrateo_entre_algunas_usa_la_alicuota_como_proporcion(self):
        crear_item(self.periodo, self.e.administrador, monto=60001, modo=PRORRATEO, unidades=[self.e.a102, self.e.b101])
        filas = self.filas()
        self.assertEqual(filas[self.e.a101].items, 0)
        self.assertEqual(sorted([filas[self.e.a102].items, filas[self.e.b101].items]), [30000, 30001])

    def test_los_items_no_cambian_el_fondo_y_el_total_cuadra(self):
        sin_items = calcular_emision(self.periodo)
        crear_item(self.periodo, self.e.administrador, monto=50000, modo=PRORRATEO)
        crear_item(self.periodo, self.e.administrador, monto=25000, unidades=[self.e.b101])
        emision = calcular_emision(self.periodo)
        self.assertEqual(emision.total_fondo, sin_items.total_fondo)
        self.assertEqual(emision.total_items, 75000)
        self.assertEqual(emision.total_a_cobrar, sin_items.total_a_cobrar + 75000)
        self.assertEqual(sum(f.total for f in emision.filas), emision.total_a_cobrar)

    def test_item_sin_unidades_que_lo_paguen_impide_emitir(self):
        cero = Unidad.objects.create(edificio=self.e.torre_b, numero="B102", alicuota=Decimal("0"))
        crear_item(self.periodo, self.e.administrador, monto=9000, modo=PRORRATEO, unidades=[cero], nombre="Cuota rara")
        emision = calcular_emision(self.periodo)
        self.assertFalse(emision.puede_emitir)
        self.assertTrue(any("Cuota rara" in error for error in emision.errores))

    def test_cobro_sobre_el_maximo_impide_emitir(self):
        crear_item(self.periodo, self.e.administrador, monto=MONTO_MAXIMO, unidades=[self.e.a101])
        emision = calcular_emision(self.periodo)
        self.assertTrue(any("supera $999.999.999" in error for error in emision.errores))


class EmisionConItemsTest(Base):
    """Criterio: el ítem aparece en el cobro del mes como línea separada y cuadra con los reportes."""

    def test_emitir_guarda_lineas_y_total(self):
        cuota = crear_item(self.periodo, self.e.administrador, monto=100000, modo=PRORRATEO, nombre="Cuota")
        multa = crear_item(self.periodo, self.e.administrador, monto=25000, unidades=[self.e.a101], nombre="Multa")
        emitir_periodo(self.periodo, usuario=self.e.administrador)

        cobro = self.cobro(self.e.a101)
        self.assertEqual(list(cobro.lineas.values_list("item", "nombre", "monto")),
                         [(cuota.pk, "Cuota", 40000), (multa.pk, "Multa", 25000)])
        self.assertEqual(cobro.monto_items, 65000)
        self.assertEqual(cobro.total, cobro.monto + cobro.monto_fondo_reserva + 65000)
        self.assertEqual(list(self.cobro(self.e.b101).lineas.values_list("nombre", flat=True)), ["Cuota"])
        self.assertEqual(LineaCobro.objects.count(), 4)

    def test_reporte_de_recaudacion_y_morosidad_incluye_los_items(self):
        crear_item(self.periodo, self.e.administrador, monto=30000, modo=PRORRATEO)
        emision = emitir_periodo(self.periodo, usuario=self.e.administrador)
        reporte = generar_reporte(PeriodoGasto.objects.get(pk=self.periodo.pk))
        self.assertEqual(reporte.total_emitido, emision.total_a_cobrar)
        self.assertEqual(reporte.total_emitido, sum(d.total for d in DetalleGastoComun.objects.all()))
        self.assertEqual(reporte.saldo_periodo, reporte.total_emitido)

    def test_el_ingreso_al_fondo_no_incluye_los_items(self):
        crear_item(self.periodo, self.e.administrador, monto=90000, modo=PRORRATEO)
        emision = emitir_periodo(self.periodo, usuario=self.e.administrador)
        self.assertEqual(self.periodo.ingreso_fondo.monto, emision.total_fondo)

    def test_sin_items_el_cobro_no_cambia(self):
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        cobro = self.cobro(self.e.a101)
        self.assertEqual(cobro.monto_items, 0)
        self.assertEqual(cobro.total, cobro.monto + cobro.monto_fondo_reserva)
        self.assertFalse(LineaCobro.objects.exists())

    def test_un_item_ya_cobrado_no_se_borra_suelto(self):
        """Borrarlo dejaría monto_items sin sus líneas; con su período o condominio sí se borra."""
        item = crear_item(self.periodo, self.e.administrador, monto=5000)
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        with self.assertRaises(RestrictedError):
            item.delete()
        self.e.condominio.delete()
        self.assertFalse(LineaCobro.objects.exists())

    def test_el_item_va_al_mes_que_corresponde(self):
        otro = periodo_con_egreso(self.e.condominio, self.e.administrador, mes=11)
        crear_item(otro, self.e.administrador, monto=5000)
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        self.assertEqual(self.cobro(self.e.a101).monto_items, 0)


class MantenedorTest(Base):
    """Criterios: solo el administrador crea, edita y elimina; período emitido bloqueado; auditoría."""

    def datos(self, **cambios):
        return {"nombre": "Multa por ruidos", "modo": POR_UNIDAD, "monto": "25.000", "alcance": ALGUNAS,
                "unidades": [self.e.a101.pk], **cambios}

    def url_nuevo(self, periodo=None):
        return reverse("gastos:item_nuevo", args=[(periodo or self.periodo).pk])

    def auditoria(self, accion):
        return RegistroAuditoria.objects.filter(objeto_tipo="itemcobro", accion=accion)

    def test_administrador_crea_edita_y_elimina_con_auditoria(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(self.url_nuevo(), self.datos())
        self.assertRedirects(respuesta, self.periodo.get_absolute_url())
        item = ItemCobro.objects.get()
        self.assertEqual((item.monto, list(item.unidades.all()), item.creado_por), (25000, [self.e.a101], self.e.administrador))
        creado = self.auditoria("crear").get()
        self.assertEqual(creado.despues["unidades"], [str(self.e.a101)])
        self.assertEqual(creado.usuario_id, self.e.administrador.pk)

        self.client.post(reverse("gastos:item_editar", args=[item.pk]), self.datos(monto="30.000"))
        cambio = self.auditoria("modificar").get()
        self.assertEqual((cambio.antes, cambio.despues), ({"monto": 25000}, {"monto": 30000}))

        self.client.post(reverse("gastos:item_eliminar", args=[item.pk]))
        self.assertFalse(ItemCobro.objects.exists())
        self.assertEqual(self.auditoria("eliminar").get().antes["nombre"], "Multa por ruidos")

    def test_el_comite_ve_los_items_en_el_detalle(self):
        crear_item(self.periodo, self.e.administrador, monto=25000, nombre="Multa visible")
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(self.periodo.get_absolute_url())
        self.assertContains(respuesta, "Multa visible")
        self.assertNotContains(respuesta, self.url_nuevo())

    def test_comite_conserje_y_residente_reciben_403(self):
        item = crear_item(self.periodo, self.e.administrador, monto=25000)
        rutas = [self.url_nuevo(), reverse("gastos:item_editar", args=[item.pk]),
                 reverse("gastos:item_eliminar", args=[item.pk])]
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            for ruta in rutas:
                with self.subTest(usuario=usuario.email, ruta=ruta):
                    self.assertEqual(self.client.get(ruta).status_code, 403)
                    self.assertEqual(self.client.post(ruta, self.datos(monto="1")).status_code, 403)
        self.assertEqual(ItemCobro.objects.get().monto, 25000)
        self.assertEqual(self.auditoria("crear").count(), 1)

    def test_otro_condominio_responde_404(self):
        ajeno = periodo_con_egreso(self.e.ajeno, self.e.administrador)
        item = crear_item(ajeno, self.e.administrador, monto=1000)
        self.client.force_login(self.e.administrador)
        for ruta in (self.url_nuevo(ajeno), reverse("gastos:item_editar", args=[item.pk]),
                     reverse("gastos:item_eliminar", args=[item.pk])):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)
                self.assertEqual(self.client.post(ruta, self.datos()).status_code, 404)
        self.assertTrue(ItemCobro.objects.filter(pk=item.pk, monto=1000).exists())
        self.assertEqual(self.auditoria("modificar").count() + self.auditoria("eliminar").count(), 0)

    def test_alcance_algunas_exige_unidades_del_condominio(self):
        self.client.force_login(self.e.administrador)
        for unidades in ([], [self.e.unidad_ajena.pk]):
            with self.subTest(unidades=unidades):
                respuesta = self.client.post(self.url_nuevo(), self.datos(unidades=unidades))
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].errors["unidades"])
        self.assertFalse(ItemCobro.objects.exists())

    def test_alcance_todas_ignora_las_unidades_marcadas(self):
        self.client.force_login(self.e.administrador)
        self.client.post(self.url_nuevo(), self.datos(alcance=TODAS))
        self.assertFalse(ItemCobro.objects.get().unidades.exists())

    def test_periodo_emitido_no_admite_cambios(self):
        item = crear_item(self.periodo, self.e.administrador, monto=25000)
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        self.client.force_login(self.e.administrador)
        for ruta, datos in [(self.url_nuevo(), self.datos()),
                            (reverse("gastos:item_editar", args=[item.pk]), self.datos(monto="1")),
                            (reverse("gastos:item_eliminar", args=[item.pk]), {})]:
            with self.subTest(ruta=ruta):
                self.assertRedirects(self.client.get(ruta), self.periodo.get_absolute_url())
                respuesta = self.client.post(ruta, datos, follow=True)
                self.assertContains(respuesta, "sus ítems de cobro no se pueden modificar")
        self.assertEqual(list(ItemCobro.objects.values_list("monto", flat=True)), [25000])

    def test_el_servicio_rechaza_si_la_emision_gano_la_carrera(self):
        """La vista ya pasó PeriodoAbiertoMixin, pero el período se emitió antes de guardar."""
        item = crear_item(self.periodo, self.e.administrador, monto=25000)
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        item.monto = 1
        with self.assertRaises(ValidationError):
            guardar_item(item, [], usuario=self.e.administrador)
        with self.assertRaises(ValidationError):
            eliminar_item(item, usuario=self.e.administrador)
        self.assertEqual(ItemCobro.objects.get().monto, 25000)


class ResidenteVeSoloLoSuyoTest(Base):
    """Criterio: el residente ve solo los ítems de su unidad y de su residencia (#46)."""

    def setUp(self):
        super().setUp()
        crear_item(self.periodo, self.e.administrador, monto=25000, unidades=[self.e.b101], nombre="Multa B101")
        crear_item(self.periodo, self.e.administrador, monto=10000, nombre="Cuota general")
        emitir_periodo(self.periodo, usuario=self.e.administrador)

    def lineas_de(self, usuario):
        cobros = cobros_del_residente(usuario, self.e.condominio)
        return set(LineaCobro.objects.filter(detalle__in=cobros).values_list("nombre", "detalle__unidad"))

    def test_solo_las_lineas_de_su_unidad(self):
        self.assertEqual(self.lineas_de(self.e.residente), {("Cuota general", self.e.a101.pk)})
        self.assertEqual(self.lineas_de(self.e.residente_b),
                         {("Cuota general", self.e.b101.pk), ("Multa B101", self.e.b101.pk)})

    def test_no_ve_items_de_antes_de_su_residencia(self):
        nuevo = crear_usuario("nuevo@prueba.cl")
        Residente.objects.create(usuario=nuevo, unidad=self.e.b101, desde=date(2026, 11, 1))
        self.assertEqual(self.lineas_de(nuevo), set())

    def test_el_total_adeudado_incluye_los_items(self):
        cobros = list(cobros_del_residente(self.e.residente_b, self.e.condominio))
        cobro = self.cobro(self.e.b101)
        self.assertEqual(total_adeudado(cobros), cobro.monto + cobro.monto_fondo_reserva + 35000)


@skipUnlessDBFeature("has_select_for_update")
class ItemsConcurrenciaTest(TransactionTestCase):
    """Criterio: un ítem guardado mientras se emite no descuadra lo cobrado (MySQL real)."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = periodo_con_egreso(self.e.condominio, self.e.administrador)

    def test_guardar_item_y_emitir_a_la_vez(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.db import connections

        self.assertEqual(connection.vendor, "mysql")
        barrera = Barrier(2)

        def en_paralelo(operacion):
            try:
                barrera.wait(timeout=10)
                operacion()
                return "ok"
            except ValidationError:
                return "rechazado"
            finally:
                connections.close_all()

        item = ItemCobro(periodo=self.periodo, nombre="Multa", modo=POR_UNIDAD, monto=25000, alcance=TODAS,
                         creado_por=self.e.administrador)
        with ThreadPoolExecutor(max_workers=2) as hilos:
            emision = hilos.submit(en_paralelo, lambda: emitir_periodo(self.periodo))
            guardado = hilos.submit(en_paralelo, lambda: guardar_item(item, [], usuario=self.e.administrador))
            resultados = (emision.result(timeout=30), guardado.result(timeout=30))

        self.assertEqual(resultados[0], "ok")
        # O el ítem entró antes y se cobró a las 3 unidades, o llegó tarde y se rechazó: nunca a medias.
        cobrado = sum(DetalleGastoComun.objects.values_list("monto_items", flat=True))
        if resultados[1] == "ok":
            self.assertEqual((ItemCobro.objects.count(), cobrado, LineaCobro.objects.count()), (1, 75000, 3))
        else:
            self.assertEqual((ItemCobro.objects.count(), cobrado, LineaCobro.objects.count()), (0, 0, 0))
