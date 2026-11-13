"""Ayudas, leyenda de obligatorios y secciones en los formularios principales (Issue #78)."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto

LEYENDA = "Los campos con * son obligatorios."


class AyudasEnFormulariosTest(TestCase):
    """Cada página de formulario trae sus ayudas clave, la leyenda (una vez) y, si es larga, sus secciones."""

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10)
        self.egreso = Egreso.objects.create(
            periodo=self.periodo, categoria="ASEO", descripcion="Aseo", monto=1000, creado_por=self.e.administrador
        )
        self.cobro = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000
        )

    def comprobar(self, url, ayudas, secciones=(), usuario=None, obligatorios=True):
        self.client.force_login(usuario or self.e.administrador)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        if obligatorios:
            self.assertContains(respuesta, LEYENDA, count=1)
        else:
            self.assertNotContains(respuesta, LEYENDA)
        for texto in ayudas:
            self.assertContains(respuesta, texto)
        for numero, titulo in enumerate(secciones, start=1):
            self.assertContains(respuesta, f'<span class="seccion-numero" aria-hidden="true">{numero}</span>{titulo}</h2>')
        if not secciones:
            self.assertNotContains(respuesta, "seccion-numero")

    # --- formularios largos, en tarjetas numeradas
    def test_egreso(self):
        self.comprobar(
            reverse("gastos:egreso_nuevo", args=[self.periodo.pk]),
            ["Agrupa el gasto en el resumen del período.", "Opcional. Déjalo en «Sin proveedor»",
             'placeholder="Ej.: Reposición de luminarias del pasillo"', "Se suma al total que se reparte"],
            ["Gasto", "Monto y documento"],
        )

    def test_egreso_al_editar(self):
        self.comprobar(
            reverse("gastos:egreso_editar", args=[self.egreso.pk]), ["Fecha de la boleta o factura."],
            ["Gasto", "Monto y documento"],
        )

    def test_periodo(self):
        self.comprobar(
            reverse("gastos:periodo_nuevo"),
            ["Mínimo 5 % (Ley 21.442).", "Opcional. Último día para pagar", "Opcional. Artículo del reglamento",
             "Solo puede haber un período por mes."],
            ["Período", "Reparto", "Pago"],
        )

    def test_alta_de_usuario(self):
        self.comprobar(
            reverse("cuentas:usuario_nuevo"),
            ["Recibirá aquí la invitación", "no puede estar en dos cuentas", 'placeholder="Ej.: maria.soto@example.com"',
             "Define qué puede hacer en este condominio"],
            ["Datos de la persona", "Rol en el condominio"],
        )

    def test_unidad(self):
        self.comprobar(
            reverse("condominios:unidad_nueva"),
            ["Fracción del total de gastos comunes", 'placeholder="Ej.: 0.012500"', "Los subterráneos van con número negativo"],
            ["Ubicación", "Tipo y prorrateo"],
        )

    # --- formularios cortos (siguen con _formulario.html)
    def test_perfil(self):
        self.comprobar(
            reverse("cuentas:perfil"),
            ["Opcional. La administración lo usa para contactarte", 'placeholder="Ej.: +56 9 1234 5678"'],
            obligatorios=False,  # en el perfil todos los campos son opcionales: no hay leyenda
        )

    def test_edificio(self):
        self.comprobar(reverse("condominios:edificio_nuevo"), ["Opcional. Solo si es distinta", 'placeholder="Ej.: Torre A"'])

    def test_espacio(self):
        self.comprobar(
            reverse("reservas:espacio_nuevo"),
            ["escribe 0 si es gratis", "Opcional. Qué incluye el espacio", 'placeholder="Ej.: Quincho"'],
        )

    def test_reserva(self):
        self.comprobar(
            reverse("reservas:nueva"),
            ["Debe estar dentro del horario del espacio.", "no toparse con otra reserva"],
            usuario=self.e.residente,
        )

    def test_comunicado(self):
        self.comprobar(
            reverse("comunicados:nuevo"),
            ["Opcional. Solo si el comunicado es para un edificio.", "Los fijados aparecen primero", 'placeholder="Ej.: Corte de agua'],
        )

    def test_pago(self):
        self.comprobar(
            reverse("pagos:registrar_pago", args=[self.cobro.pk]),
            ["abono parcial", "No puede ser futura.", "Opcional. Nota interna"],
        )

    def test_proveedor(self):
        self.comprobar(
            reverse("proveedores:nuevo"),
            ["Opcional. A quién llamar", "Nombre legal, como aparece en sus facturas.", 'placeholder="Ej.: Ascensores del Sur SpA"'],
        )

    def test_incidente(self):
        self.comprobar(
            reverse("incidentes:nuevo"),
            ["Opcional. Déjalo vacío si el incidente es en un área común.", "Cuenta qué ocurre, dónde y desde cuándo"],
            usuario=self.e.residente,
        )

    def test_residente_conserva_su_formulario_sin_secciones(self):
        self.comprobar(reverse("condominios:residente_nuevo", args=[self.e.a101.pk]), ["Desde cuándo vive en la unidad"])

    def test_sin_campos_obligatorios_no_hay_leyenda(self):
        """La leyenda sale solo si algún campo visible es obligatorio."""
        from django import forms
        from django.template.loader import render_to_string

        class Opcional(forms.Form):
            nota = forms.CharField(required=False)

        html = render_to_string("_formulario_cabecera.html", {"form": Opcional()})
        self.assertNotIn(LEYENDA, html)


class MaximoDelEgresoTest(TestCase):
    """Issue #78: el error del máximo se escribe con puntos de miles."""

    def test_mensaje_con_puntos(self):
        e = crear_escenario()
        periodo = PeriodoGasto.objects.create(condominio=e.condominio, anio=2026, mes=10)
        self.client.force_login(e.administrador)
        datos = {"categoria": "ASEO", "descripcion": "Aseo", "fecha": "2026-10-05", "proveedor": ""}
        for monto in ["1.000.000.000", "1000000000"]:
            respuesta = self.client.post(reverse("gastos:egreso_nuevo", args=[periodo.pk]), {**datos, "monto": monto})
            self.assertEqual(respuesta.context["form"].errors["monto"], ["El monto no puede superar $999.999.999."])
        self.assertFalse(Egreso.objects.exists())
