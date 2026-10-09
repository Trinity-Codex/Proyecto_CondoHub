"""Pruebas del estado de cuenta del residente (Issue #3, RF03)."""
import datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.condominios.models import Membresia
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto
from apps.gastos.servicios import emitir_periodo
from apps.notificaciones.models import Notificacion

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

    def test_la_notificacion_de_emision_lleva_al_estado_de_cuenta(self):
        """Ajuste de la revisión: antes la campana llevaba al panel de inicio."""
        Egreso.objects.create(
            periodo=self.nov, categoria="ASEO", descripcion="Aseo de noviembre", monto=100000,
            creado_por=self.e.administrador,
        )
        emitir_periodo(self.nov)
        notificacion = Notificacion.objects.filter(usuario=self.e.residente, titulo="Gastos comunes emitidos").get()
        self.assertEqual(notificacion.url, reverse("pagos:estado_cuenta"))

    def test_el_detalle_muestra_el_criterio_de_reparto(self):
        cobro = self.cobro(self.oct, self.e.a101)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[cobro.pk]))
        self.assertContains(respuesta, "Según la alícuota de cada unidad")

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

class RegistrarPagosTest(TestCase):
    """Issue #4 (RF04): el administrador registra pagos, totales o parciales, sin pagar de más."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=10, estado=PeriodoGasto.Estado.EMITIDO
        )
        # Cobro de A101 por $42.000 (40.000 + 2.000 de fondo de reserva).
        self.cobro = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000
        )
        self.url = reverse("pagos:registrar_pago", args=[self.cobro.pk])
        # Administrador de otro condominio: no debe poder tocar los cobros de este.
        self.admin_ajeno = crear_usuario("admin.ajeno@prueba.cl")
        Membresia.objects.create(usuario=self.admin_ajeno, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)

    def datos(self, monto, **extra):
        return {"monto": monto, "fecha": timezone.localdate().isoformat(), "medio": "TRANSFERENCIA", "observacion": "", **extra}

    def pagar(self, monto, **extra):
        self.client.force_login(self.e.administrador)
        return self.client.post(self.url, self.datos(monto, **extra))

    def test_pago_total_deja_el_cobro_pagado(self):
        respuesta = self.pagar(42000)
        self.assertRedirects(respuesta, reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PAGADO)
        pago = self.cobro.pagos.get()
        self.assertEqual(pago.monto, 42000)
        self.assertEqual(pago.registrado_por, self.e.administrador)

    def test_pagos_parciales_suman_hasta_pagar_el_cobro(self):
        self.pagar(10000)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PENDIENTE)  # todavía falta
        self.pagar(32000)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PAGADO)
        self.assertEqual(self.cobro.pagos.count(), 2)

    def test_un_cobro_moroso_pasa_a_pagado_al_completarse(self):
        DetalleGastoComun.objects.filter(pk=self.cobro.pk).update(estado=Estado.MOROSO)
        self.pagar(42000)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PAGADO)

    def test_no_se_puede_pagar_mas_de_lo_adeudado(self):
        respuesta = self.pagar(42001)
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        self.assertIn("monto", respuesta.context["form"].errors)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_el_saldo_tiene_en_cuenta_los_pagos_anteriores(self):
        self.pagar(40000)
        respuesta = self.pagar(2001)  # solo faltan 2.000
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cobro.pagos.count(), 1)

    def test_no_se_paga_un_cobro_ya_pagado(self):
        self.pagar(42000)
        respuesta = self.pagar(1)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.cobro.pagos.count(), 1)

    def test_monto_cero_o_negativo_se_rechaza(self):
        for monto in (0, -5):
            self.assertEqual(self.pagar(monto).status_code, 200)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_fecha_futura_se_rechaza(self):
        manana = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.pagar(1000, fecha=manana).status_code, 200)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_registrar_avisa_al_residente_de_la_unidad(self):
        self.pagar(42000)
        aviso = Notificacion.objects.get(usuario=self.e.residente, titulo="Registramos tu pago")
        self.assertEqual(aviso.url, reverse("pagos:cobro_detalle", args=[self.cobro.pk]))
        # Los residentes de otras unidades no reciben nada.
        self.assertFalse(Notificacion.objects.filter(usuario=self.e.residente_b, titulo="Registramos tu pago").exists())

    def test_solo_el_administrador_registra_pagos(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, self.datos(1000)).status_code, 403)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_un_cobro_de_otro_condominio_da_404(self):
        self.client.force_login(self.admin_ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.datos(1000)).status_code, 404)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_cobranza_y_cuenta_de_unidad_para_administrador_y_comite(self):
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("pagos:cobranza")).status_code, 200)
            self.assertEqual(self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk])).status_code, 200)
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("pagos:cobranza")).status_code, 403)

    def test_el_comite_ve_la_cuenta_pero_sin_boton_de_registrar(self):
        self.client.force_login(self.e.comite)
        respuesta = self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.assertNotContains(respuesta, self.url)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.assertContains(respuesta, self.url)

    def test_la_cuenta_de_una_unidad_ajena_da_404(self):
        self.client.force_login(self.admin_ajeno)
        self.assertEqual(self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk])).status_code, 404)

    def test_la_deuda_descuenta_los_pagos_parciales(self):
        self.pagar(10000)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(respuesta.context["total_adeudado"], 32000)
        inicio = self.client.get(reverse("core:inicio"))
        self.assertEqual(inicio.context["mi_deuda"], 32000)

    def test_el_residente_ve_sus_pagos_en_el_detalle(self):
        self.pagar(10000)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[self.cobro.pk]))
        self.assertEqual(respuesta.context["pagado"], 10000)
        self.assertEqual(respuesta.context["saldo"], 32000)
        self.assertEqual(respuesta.context["pagos"].count(), 1)

    def test_los_reportes_pueden_sumar_los_pagos_por_el_nombre_acordado(self):
        """Contrato con Walther (#5): detalle.pagos y la columna monto."""
        self.pagar(10000)
        self.pagar(5000)
        from django.db.models import Sum

        total = DetalleGastoComun.objects.filter(pk=self.cobro.pk).aggregate(t=Sum("pagos__monto"))["t"]
        self.assertEqual(total, 15000)
