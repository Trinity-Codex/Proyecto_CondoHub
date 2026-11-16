"""Pulido visual de pagos (Issue #97): insignias y tarjeta compartidas, sin cambiar importes ni permisos."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto

Estado = DetalleGastoComun.Estado


class InsigniasDePagosTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=10, estado=PeriodoGasto.Estado.EMITIDO
        )
        self.cobro = DetalleGastoComun.objects.create(
            periodo=periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000, estado=Estado.MOROSO
        )

    def test_cada_estado_usa_su_insignia_y_ninguna_es_badge_de_bootstrap(self):
        casos = {
            Estado.PAGADO: ("insignia-al-dia", "Pagado"),
            Estado.MOROSO: ("insignia-moroso", "Moroso"),
            Estado.PENDIENTE: ("insignia-con-deuda", "Pendiente"),
        }
        for estado, (clase, texto) in casos.items():
            DetalleGastoComun.objects.filter(pk=self.cobro.pk).update(estado=estado)
            # La cuenta de la unidad la ve el administrador; "Mi estado de cuenta", el residente.
            pantallas = (
                (self.e.administrador, reverse("pagos:cuenta_unidad", args=[self.e.a101.pk])),
                (self.e.residente, reverse("pagos:estado_cuenta")),
            )
            for usuario, url in pantallas:
                with self.subTest(estado=estado, url=url):
                    self.client.force_login(usuario)
                    respuesta = self.client.get(url)
                    self.assertContains(respuesta, f'<span class="insignia {clase}">{texto}</span>', html=True)
                    self.assertNotContains(respuesta, "badge text-bg")

    def test_la_tarjeta_de_deuda_se_comparte_en_cuenta_y_estado_de_cuenta(self):
        self.client.force_login(self.e.administrador)
        cuenta = self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.assertContains(cuenta, '<span class="insignia insignia-con-deuda">Con deuda</span>', html=True)
        self.assertContains(cuenta, "$42.000")
        DetalleGastoComun.objects.filter(pk=self.cobro.pk).update(estado=Estado.PAGADO)
        al_dia = self.client.get(reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.assertContains(al_dia, '<span class="insignia insignia-al-dia">Al día</span>', html=True)

    def test_el_detalle_del_cobro_tiene_titulo_y_estado_con_insignia(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[self.cobro.pk]))
        self.assertContains(respuesta, "<h1", count=1)
        self.assertContains(respuesta, '<span class="insignia insignia-moroso">Moroso</span>', html=True)
        self.assertContains(respuesta, "$42.000")
