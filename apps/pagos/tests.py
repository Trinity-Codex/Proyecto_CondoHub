"""Pruebas del estado de cuenta del residente (Issue #3, RF03)."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto

Estado = DetalleGastoComun.Estado


class EstadoCuentaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        emitido = PeriodoGasto.Estado.EMITIDO
        # Tres períodos ya emitidos y uno todavía abierto, todos del condominio de pruebas.
        self.ago = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=8, estado=emitido)
        self.sep = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=9, estado=emitido)
        self.oct = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10, estado=emitido)
        self.nov = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=11)
        Egreso.objects.create(
            periodo=self.oct, categoria="ASEO", descripcion="Aseo de octubre", monto=100000,
            creado_por=self.e.administrador,
        )

    def cobro(self, periodo, unidad, estado=Estado.PENDIENTE, monto=40000, fondo=2000):
        """Crea un cobro; por defecto el total es 42.000."""
        return DetalleGastoComun.objects.create(
            periodo=periodo, unidad=unidad, monto=monto, monto_fondo_reserva=fondo, estado=estado
        )

    def test_residente_ve_solo_sus_cobros_emitidos(self):
        propio = self.cobro(self.oct, self.e.a101)
        self.cobro(self.oct, self.e.b101)  # cobro de otro residente
        self.cobro(self.nov, self.e.a101)  # período aún abierto: no se cobra todavía
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(list(respuesta.context["cobros"]), [propio])

    def test_total_adeudado_suma_pendientes_y_morosos_pero_no_pagados(self):
        self.cobro(self.ago, self.e.a101, estado=Estado.PAGADO)     # no se debe
        self.cobro(self.sep, self.e.a101, estado=Estado.MOROSO)     # 42.000
        self.cobro(self.oct, self.e.a101, estado=Estado.PENDIENTE)  # 42.000
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(len(respuesta.context["cobros"]), 3)  # el pagado también se muestra
        self.assertEqual(respuesta.context["total_adeudado"], 84000)

    def test_residente_al_dia_no_debe_nada(self):
        self.cobro(self.oct, self.e.a101, estado=Estado.PAGADO)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(respuesta.context["total_adeudado"], 0)

    def test_residente_ve_el_detalle_de_su_cobro(self):
        cobro = self.cobro(self.oct, self.e.a101)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[cobro.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_egresos"], 100000)

    def test_residente_no_puede_ver_el_detalle_de_otro(self):
        ajeno = self.cobro(self.oct, self.e.b101)
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("pagos:cobro_detalle", args=[ajeno.pk])).status_code, 404)

    def test_no_se_ve_el_detalle_de_un_periodo_abierto(self):
        abierto = self.cobro(self.nov, self.e.a101)
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("pagos:cobro_detalle", args=[abierto.pk])).status_code, 404)

    def test_residente_de_otro_condominio_no_ve_cobros(self):
        self.cobro(self.oct, self.e.a101)
        self.client.force_login(self.e.residente_ajeno)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(len(respuesta.context["cobros"]), 0)

    def test_otros_roles_no_entran(self):
        for usuario in (self.e.administrador, self.e.comite, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("pagos:estado_cuenta")).status_code, 403)

    def test_tarjeta_mi_deuda_en_el_inicio(self):
        self.cobro(self.oct, self.e.a101)  # 42.000
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.context["mi_deuda"], 42000)
        self.assertContains(respuesta, "Mi deuda")

    def test_el_menu_muestra_mi_cuenta_solo_a_residentes(self):
        self.client.force_login(self.e.residente)
        self.assertContains(self.client.get(reverse("core:inicio")), "Mi cuenta")
        self.client.force_login(self.e.administrador)
        self.assertNotContains(self.client.get(reverse("core:inicio")), "Mi cuenta")