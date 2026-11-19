"""Rendición mensual: importes, descarga y permisos."""
from datetime import date
from io import BytesIO

from pypdf import PdfReader
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, Egreso, MovimientoFondo, PeriodoGasto
from apps.pagos.models import Pago
from apps.proveedores.models import Proveedor


class InicioTest(TestCase):
    """Entran el administrador y el comité (200); los demás roles reciben 403 y sin sesión se pide iniciarla."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("rendicion:inicio")

    def test_quien_puede_entrar(self):
        esperados = [
            (self.e.administrador, 200),
            (self.e.comite, 200),
            (self.e.conserje, 403),
            (self.e.residente, 403),
        ]
        for usuario, esperado in esperados:
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, esperado)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(
            respuesta, reverse("cuentas:iniciar_sesion") + "?next=" + self.url, fetch_redirect_response=False
        )

    def test_el_menu_tiene_el_enlace(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("core:inicio")), self.url)


class RendicionMensualTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10, estado="EMITIDO")
        self.cobro = DetalleGastoComun.objects.create(periodo=self.periodo, unidad=self.e.a101,
                                                      monto=10000, monto_fondo_reserva=500)
        self.client.force_login(self.e.comite)

    def test_concilia_caja_cobros_anulaciones_y_fondo_en_html_y_pdf(self):
        dia = date(2026, 10, 15)
        Pago.objects.create(detalle=self.cobro, monto=3000, fecha=dia)
        Pago.objects.create(detalle=self.cobro, monto=200, fecha=date(2026, 11, 1))
        Pago.objects.create(detalle=self.cobro, monto=750, fecha=dia, anulado=True, motivo_anulacion="Duplicado")
        empresa = Proveedor.objects.create(condominio=self.e.condominio, razon_social="Servicios Demo")
        Egreso.objects.create(periodo=self.periodo, fecha=dia, monto=1400, categoria="ASEO",
                              proveedor=empresa, creado_por=self.e.administrador)
        MovimientoFondo.objects.create(condominio=self.e.condominio, periodo=self.periodo, tipo="INGRESO",
                                        monto=500, fecha=dia, descripcion="Aporte mensual")
        html = self.client.get(reverse("rendicion:detalle", args=[self.periodo.pk]))
        self.assertEqual(html.context["caja"], {"ingresos": 3000, "egresos": 1400, "saldo": 1600})
        self.assertEqual(html.context["reporte"].total_recaudado, 3200)
        pdf = self.client.get(reverse("rendicion:pdf", args=[self.periodo.pk]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        texto = " ".join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        for valor in ["Servicios Demo", "Duplicado", "Aporte mensual", "$500", "$3.200", "$1.600"]:
            self.assertContains(html, valor)
            self.assertIn(valor, texto)
        self.client.force_login(self.e.residente)
        aviso = self.client.get(reverse("pagos:aviso_cobro", args=[self.cobro.pk]))
        texto = " ".join(" ".join(p.extract_text() for p in PdfReader(BytesIO(aviso.content)).pages).split())
        self.assertIn("Saldo del fondo de reserva al cierre: $ 500", texto)
        self.assertNotIn("Duplicado", texto)

    def test_fondo_sin_cobertura_se_distingue_de_saldo_cero(self):
        html = self.client.get(reverse("rendicion:detalle", args=[self.periodo.pk]))
        self.assertContains(html, "Histórico no disponible")
        self.assertIsNone(html.context["saldo_fondo"])

    def test_periodo_emitido_permisos_y_aislamiento(self):
        ajeno = PeriodoGasto.objects.create(condominio=self.e.ajeno, anio=2026, mes=10, estado="EMITIDO")
        abierto = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=11)
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            self.assertEqual(list(self.client.get(reverse("rendicion:inicio")).context["periodos"]), [self.periodo])
            for nombre in ("detalle", "pdf"):
                for excluido in (ajeno, abierto):
                    self.assertEqual(self.client.get(reverse("rendicion:"+nombre, args=[excluido.pk])).status_code, 404)
                self.assertEqual(self.client.get(reverse("rendicion:"+nombre, args=[self.periodo.pk])).status_code, 200)
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            for nombre in ("detalle", "pdf"):
                self.assertEqual(self.client.get(reverse("rendicion:"+nombre, args=[self.periodo.pk])).status_code, 403)
