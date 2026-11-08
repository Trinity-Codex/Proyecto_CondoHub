"""Pruebas de core: condominio activo, permisos por rol, residentes, PDF y datos demo."""
import tempfile
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.db.models import Count, Sum
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from pypdf import PdfReader

from apps.comunicados.models import Comunicado
from apps.condominios.models import Condominio, Edificio, Membresia, Residente, Unidad
from apps.core.pdf import ErrorPDF, _resolver_estatico, generar_pdf, renderizar_pdf
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.cuentas.models import Usuario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto
from apps.gastos.reportes import generar_reporte
from apps.incidentes.models import Incidente
from apps.notificaciones.models import Notificacion
from apps.pagos.models import Pago
from apps.proveedores.models import Proveedor
from apps.reservas.models import EspacioComun, Reserva


class CondominioActivoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertRedirects(respuesta, reverse("cuentas:iniciar_sesion") + "?next=/", fetch_redirect_response=False)

    def test_usuario_sin_condominio(self):
        self.client.force_login(crear_usuario("nadie@prueba.cl"))
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertRedirects(respuesta, reverse("core:sin_condominio"))

    def test_toma_el_condominio_del_usuario(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.wsgi_request.condominio, self.e.condominio)
        self.assertEqual(respuesta.wsgi_request.roles, {Membresia.Rol.RESIDENTE})

    def test_no_puede_cambiar_a_un_condominio_ajeno(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("core:cambiar_condominio", args=[self.e.ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_cambiar_de_condominio(self):
        # El administrador pasa a tener acceso a los dos condominios.
        Membresia.objects.create(usuario=self.e.administrador, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("core:cambiar_condominio", args=[self.e.ajeno.pk]))
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.wsgi_request.condominio, self.e.ajeno)

    def test_panel_del_administrador_muestra_resumen(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.context["resumen"]["unidades"], 3)
        self.assertEqual(respuesta.context["suma_alicuotas"], Decimal("1"))

    def test_residente_no_ve_el_resumen(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertNotIn("resumen", respuesta.context)


class ResidenteTest(TestCase):
    def test_registrar_residente_le_da_el_rol(self):
        e = crear_escenario()
        self.assertTrue(
            Membresia.objects.filter(usuario=e.residente, condominio=e.condominio, rol=Membresia.Rol.RESIDENTE).exists()
        )

    def test_unidades_solo_para_admin_y_comite(self):
        e = crear_escenario()
        for usuario, esperado in [(e.administrador, 200), (e.comite, 200), (e.residente, 403), (e.conserje, 403)]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("condominios:unidades")).status_code, esperado, usuario)


class MenuAdministracionTest(TestCase):
    """
    Menú principal: los enlaces de gestión van en el desplegable "Administración"
    (así la barra cabe en una línea) y cada página marca solo su propio enlace.
    """

    def setUp(self):
        self.e = crear_escenario()

    def menu(self, usuario, url_name="core:inicio"):
        self.client.force_login(usuario)
        return self.client.get(reverse(url_name))

    def test_el_administrador_ve_todo_dentro_de_administracion(self):
        respuesta = self.menu(self.e.administrador)
        self.assertContains(respuesta, "Administración")
        for ruta in ("condominios:unidades", "cuentas:usuarios", "gastos:periodos", "pagos:cobranza",
                     "gastos:reporte", "proveedores:lista", "cartera:inicio", "rendicion:inicio", "auditoria:inicio"):
            self.assertContains(respuesta, f'class="dropdown-item " href="{reverse(ruta)}"')

    def test_el_comite_no_ve_usuarios(self):
        respuesta = self.menu(self.e.comite)
        self.assertContains(respuesta, "Administración")
        self.assertNotContains(respuesta, reverse("cuentas:usuarios"))

    def test_el_comite_ve_cartera_y_rendicion_pero_no_auditoria(self):
        # Roles provisionales del PMV (#62): auditoría es solo del administrador.
        respuesta = self.menu(self.e.comite)
        self.assertContains(respuesta, reverse("cartera:inicio"))
        self.assertContains(respuesta, reverse("rendicion:inicio"))
        self.assertNotContains(respuesta, reverse("auditoria:inicio"))

    def test_las_apps_nuevas_marcan_administracion(self):
        respuesta = self.menu(self.e.administrador, "cartera:inicio")
        self.assertContains(respuesta, 'class="nav-link dropdown-toggle active"')
        self.assertContains(respuesta, f'class="dropdown-item active" href="{reverse("cartera:inicio")}"')

    def test_residentes_y_conserje_no_ven_administracion(self):
        for usuario in (self.e.residente, self.e.conserje):
            self.assertNotContains(self.menu(usuario), "Administración")

    def test_cobranza_no_marca_mi_cuenta(self):
        # El comité de prueba también es residente: ve "Mi cuenta" y "Administración".
        Membresia.objects.create(usuario=self.e.residente, condominio=self.e.condominio, rol=Membresia.Rol.COMITE)
        respuesta = self.menu(self.e.residente, "pagos:cobranza")
        self.assertContains(respuesta, f'class="nav-link " href="{reverse("pagos:estado_cuenta")}"')
        self.assertContains(respuesta, f'class="dropdown-item active" href="{reverse("pagos:cobranza")}"')


class PlantillaBaseTest(TestCase):
    """base.html: los comentarios de la plantilla no deben verse en la página."""

    def test_el_inicio_de_sesion_muestra_el_aviso_de_privacidad(self):
        # Issue #62: el enlace del pie se ve sin sesión, antes de entregar datos personales.
        respuesta = self.client.get(reverse("cuentas:iniciar_sesion"))
        self.assertContains(respuesta, f'href="{reverse("privacidad:aviso")}">Aviso de privacidad</a>')

    def test_los_comentarios_de_base_no_aparecen_en_la_pagina(self):
        # En Django {# ... #} sirve solo en una línea; los de varias líneas van
        # en {% comment %}. Si no, se muestran como texto arriba de cada página.
        respuesta = self.client.get(reverse("cuentas:iniciar_sesion"))
        self.assertNotContains(respuesta, "{#")
        self.assertNotContains(respuesta, "tipografía del logotipo")
        self.assertContains(respuesta, 'integrity="sha384-', count=3)


class RenderizarPdfTest(SimpleTestCase):
    """Contrato C0 (#62): renderizar_pdf(plantilla, contexto, nombre) entrega un PDF que se abre en el navegador."""

    plantilla = "core/pdf/prueba.html"

    def test_entrega_un_pdf_con_sus_encabezados(self):
        respuesta = renderizar_pdf(self.plantilla, {}, "aviso-de-prueba")
        self.assertTrue(respuesta.content.startswith(b"%PDF-"))
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertEqual(respuesta["Content-Disposition"], 'inline; filename="aviso-de-prueba.pdf"')

    def test_el_texto_conserva_tildes_ene_y_montos(self):
        texto = PdfReader(BytesIO(generar_pdf(self.plantilla, {}))).pages[0].extract_text()
        self.assertIn("Ñuñoa", texto)
        self.assertIn("$1.234.567", texto)
        self.assertIn("Gasto común de prueba", texto)

    def test_corrige_el_nombre_del_archivo(self):
        for nombre, esperado in [
            ("aviso", "aviso.pdf"),
            ("aviso.pdf", "aviso.pdf"),
            ("aviso.PDF", "aviso.pdf"),
            ("../cobros/2026 nov", "cobros-2026_nov.pdf"),
            ("", "documento.pdf"),
            (".pdf", "documento.pdf"),
            ("/", "documento.pdf"),
        ]:
            with self.subTest(nombre=nombre):
                respuesta = renderizar_pdf(self.plantilla, {}, nombre)
                self.assertEqual(respuesta["Content-Disposition"], f'inline; filename="{esperado}"')

    def test_nombre_con_caracteres_no_ascii(self):
        respuesta = renderizar_pdf(self.plantilla, {}, "aviso-Ñuñoa")
        self.assertEqual(respuesta["Content-Disposition"], "inline; filename*=utf-8''aviso-%C3%91u%C3%B1oa.pdf")

    def test_una_ruta_fuera_de_static_se_ignora_sin_romper_el_pdf(self):
        contexto = {"imagen_extra": "/static/../config/settings.py"}
        with self.assertLogs("xhtml2pdf", level="WARNING"):
            pagina = PdfReader(BytesIO(generar_pdf(self.plantilla, contexto))).pages[0]
        self.assertEqual(len(pagina.images), 1)  # solo el logo

    def test_lee_nombres_con_hash_desde_static_root(self):
        # Con WhiteNoise (#29) {% static %} entrega "img/logo.<hash>.png", que solo existe en STATIC_ROOT.
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta, "img", "logo.3f2a.png")
            archivo.parent.mkdir()
            archivo.write_bytes(Path(settings.BASE_DIR, "static", "img", "icono-96.png").read_bytes())
            with self.settings(STATIC_ROOT=carpeta):
                self.assertEqual(_resolver_estatico("/static/img/logo.3f2a.png", None), str(archivo.resolve()))
                contexto = {"imagen_extra": "/static/img/logo.3f2a.png"}
                pagina = PdfReader(BytesIO(generar_pdf(self.plantilla, contexto))).pages[0]
        self.assertEqual(len(pagina.images), 2)

    def test_no_descarga_imagenes_externas(self):
        contexto = {"imagen_extra": "https://example.com/rastreo.png"}
        with (
            mock.patch("http.client.HTTPConnection.request") as http,
            mock.patch("http.client.HTTPSConnection.request") as https,
            self.assertLogs("xhtml2pdf", level="WARNING"),
        ):
            contenido = generar_pdf(self.plantilla, contexto)
        self.assertTrue(contenido.startswith(b"%PDF-"))
        http.assert_not_called()
        https.assert_not_called()

    def test_lee_el_logo_desde_static(self):
        pagina = PdfReader(BytesIO(generar_pdf(self.plantilla, {}))).pages[0]
        self.assertEqual(len(pagina.images), 1)

    def test_si_la_conversion_falla_lanza_error_pdf(self):
        with mock.patch("apps.core.pdf.pisa.CreatePDF", return_value=mock.Mock(err=1)):
            with self.assertRaises(ErrorPDF):
                renderizar_pdf(self.plantilla, {}, "roto")


def _por_estado(queryset):
    """{"EMITIDO": 2, "ABIERTO": 1}: cuántos registros hay en cada estado."""
    return dict(queryset.values_list("estado").annotate(n=Count("pk")).order_by("estado"))


def huella_demo():
    """
    Resumen de lo que deja cargar_demo: conteos y sumas, no claves primarias (el orden
    de creación puede cambiar al separar la demo por app sin que cambien los datos).
    """
    return {
        "usuarios": Usuario.objects.count(),
        "superusuarios": Usuario.objects.filter(is_superuser=True).count(),
        "condominios": sorted(Condominio.objects.values_list("nombre", flat=True)),
        "edificios": Edificio.objects.count(),
        "unidades": Unidad.objects.count(),
        "alicuotas": Unidad.objects.aggregate(s=Sum("alicuota"))["s"],
        "membresias": dict(Membresia.objects.values_list("rol").annotate(n=Count("pk")).order_by("rol")),
        "residentes": Residente.objects.count(),
        "espacios": EspacioComun.objects.count(),
        "reservas": _por_estado(Reserva.objects),
        "comunicados": Comunicado.objects.count(),
        "notificaciones": Notificacion.objects.count(),
        "incidentes": _por_estado(Incidente.objects),
        "proveedores": dict(Proveedor.objects.values_list("activo").annotate(n=Count("pk")).order_by("activo")),
        "periodos": _por_estado(PeriodoGasto.objects),
        "egresos": Egreso.objects.count(),
        "egresos_con_proveedor": Egreso.objects.filter(proveedor__isnull=False).count(),
        "suma_egresos": Egreso.objects.aggregate(s=Sum("monto"))["s"],
        "cobros": _por_estado(DetalleGastoComun.objects),
        "suma_cobros": DetalleGastoComun.objects.aggregate(s=Sum("monto"), f=Sum("monto_fondo_reserva")),
        "pagos": Pago.objects.count(),
        "suma_pagos": Pago.objects.aggregate(s=Sum("monto"))["s"],
    }


class CargarDemoTest(TestCase):
    """
    Issue #62: separar la demo por app (apps/<app>/demo.py) no cambia los datos que se cargan.
    HUELLA se tomó con el cargar_demo de antes de separarlo; si una app agrega datos demo
    a propósito, se actualiza el número que corresponde.
    """

    maxDiff = None
    HUELLA = {
        "usuarios": 7,
        "superusuarios": 1,
        "condominios": ["Condominio Vista Verde", "Edificio Los Aromos"],
        "edificios": 3,
        "unidades": 14,
        "alicuotas": Decimal("2"),  # cada condominio suma 1
        "membresias": {"ADMINISTRADOR": 2, "COMITE": 1, "CONSERJE": 1, "RESIDENTE": 4},
        "residentes": 4,
        "espacios": 4,
        "reservas": {"CONFIRMADA": 1},
        "comunicados": 3,
        "notificaciones": 21,
        "incidentes": {"EN_PROCESO": 1, "RECIBIDO": 1},
        "proveedores": {False: 1, True: 3},
        "periodos": {"ABIERTO": 1, "EMITIDO": 2},
        "egresos": 24,
        "egresos_con_proveedor": 9,
        "suma_egresos": 6476939,
        "cobros": {"PAGADO": 13, "PENDIENTE": 7},
        "suma_cobros": {"s": 4310739, "f": 215537},
        "pagos": 14,
        "suma_pagos": 3196063,
    }

    def cargar(self, *argumentos):
        call_command("cargar_demo", *argumentos, stdout=StringIO())

    def test_cargar_demo(self):
        self.cargar()
        self.assertEqual(huella_demo(), self.HUELLA)

    def test_cargar_demo_reiniciar(self):
        self.cargar()
        self.cargar("--reiniciar")
        self.assertEqual(huella_demo(), self.HUELLA)

    def test_sin_reiniciar_no_duplica(self):
        self.cargar()
        self.cargar()
        self.assertEqual(huella_demo(), self.HUELLA)


class IndicadoresCobranzaTest(TestCase):
    """Indicadores de cobranza en el inicio (Issue #57): los mismos números del reporte."""

    def setUp(self):
        self.e = crear_escenario()
        febrero = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=2, estado=PeriodoGasto.Estado.EMITIDO
        )
        self.marzo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=3, estado=PeriodoGasto.Estado.EMITIDO
        )
        DetalleGastoComun.objects.create(periodo=febrero, unidad=self.e.a101, monto=40000, monto_fondo_reserva=0)
        for unidad in (self.e.a101, self.e.a102, self.e.b101):
            cobro = DetalleGastoComun.objects.create(periodo=self.marzo, unidad=unidad, monto=40000, monto_fondo_reserva=0)
            if unidad == self.e.b101:
                Pago.registrar(cobro, monto=40000, registrado_por=self.e.administrador)

    def inicio(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse("core:inicio"))

    def test_administrador_y_comite_ven_los_numeros_del_reporte(self):
        reporte = generar_reporte(self.marzo)
        self.assertEqual((reporte.porcentaje_recaudacion, reporte.deuda_total, len(reporte.unidades_morosas)), (33.3, 120000, 1))
        for usuario in (self.e.administrador, self.e.comite):
            with self.subTest(usuario=usuario):
                respuesta = self.inicio(usuario)
                self.assertEqual(respuesta.context["cobranza"].periodo, self.marzo)
                self.assertContains(respuesta, "Cobranza de Marzo 2026")
                self.assertContains(respuesta, "33,3 %")
                self.assertContains(respuesta, "$120.000")
                self.assertContains(respuesta, f"{reverse('gastos:reporte')}?periodo={self.marzo.pk}")

    def test_sin_periodos_emitidos(self):
        PeriodoGasto.objects.update(estado=PeriodoGasto.Estado.ABIERTO)
        self.assertContains(self.inicio(self.e.administrador), "Aún no hay gastos comunes emitidos")

    def test_conserje_y_residente_no_los_ven(self):
        for usuario in (self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario):
                respuesta = self.inicio(usuario)
                self.assertNotIn("cobranza", respuesta.context)
                self.assertNotContains(respuesta, "Unidades morosas")
