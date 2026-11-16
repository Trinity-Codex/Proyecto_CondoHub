"""Pruebas de core: condominio activo, permisos por rol, residentes, PDF y datos demo."""
import tempfile
from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock

from django import forms
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from pypdf import PdfReader

from apps.comunicados.models import Comunicado
from apps.condominios.models import Condominio, Edificio, Membresia, Residente, Unidad
from apps.core.campos import MENSAJE_MONTO_INVALIDO, MontoField, MontoInput
from apps.core.formato import formatear_monto, normalizar_monto
from apps.core.pdf import ErrorPDF, _resolver_estatico, generar_pdf, renderizar_pdf
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.core.templatetags.condohub import pesos
from apps.cuentas.models import Usuario
from apps.gastos.models import DetalleGastoComun, Egreso, MovimientoFondo, PeriodoGasto
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
                     "gastos:reporte", "proveedores:lista", "rendicion:inicio", "auditoria:inicio"):
            self.assertContains(respuesta, f'class="dropdown-item " href="{reverse(ruta)}"')

    def test_el_comite_no_ve_usuarios(self):
        respuesta = self.menu(self.e.comite)
        self.assertContains(respuesta, "Administración")
        self.assertNotContains(respuesta, reverse("cuentas:usuarios"))

    def test_el_comite_ve_rendicion_pero_no_auditoria_ni_cartera(self):
        # Roles provisionales del PMV (#62): auditoría es solo del administrador. La cartera ya no es
        # suya: es del administrador general (#54), así que no aparece en el menú de ningún rol del condominio.
        respuesta = self.menu(self.e.comite)
        self.assertContains(respuesta, reverse("rendicion:inicio"))
        self.assertNotContains(respuesta, reverse("auditoria:inicio"))
        self.assertNotContains(respuesta, reverse("cartera:inicio"))

    def test_las_apps_nuevas_marcan_administracion(self):
        respuesta = self.menu(self.e.administrador, "rendicion:inicio")
        self.assertContains(respuesta, 'class="nav-link dropdown-toggle active"')
        self.assertContains(respuesta, f'class="dropdown-item active" href="{reverse("rendicion:inicio")}"')

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
        "movimientos_fondo": {fila["tipo"]: {"cantidad": fila["n"], "suma": fila["s"]}
            for fila in MovimientoFondo.objects.values("tipo").annotate(n=Count("pk"), s=Sum("monto")).order_by("tipo")},
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
        "usuarios": 8,  # + gerencia@condohub.cl, el administrador general (#54)
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
        # 21 y no 22: el aviso de Pago.registrar solo llega a quien ve el cobro
        # (residencia vigente); el residente recién llegado de demo.py no lo recibe.
        "notificaciones": 21,
        "incidentes": {"EN_PROCESO": 1, "RECIBIDO": 1},
        "proveedores": {False: 1, True: 3},
        "periodos": {"ABIERTO": 1, "EMITIDO": 3},  # + el mes anterior de Los Aromos (#54)
        "egresos": 28,
        "egresos_con_proveedor": 9,
        "suma_egresos": 7155439,
        "movimientos_fondo": {
            "INICIAL": {"cantidad": 2, "suma": 1500000},
            "INGRESO": {"cantidad": 3, "suma": 249462},
            "EGRESO": {"cantidad": 1, "suma": -75000},
        },
        "cobros": {"PAGADO": 13, "PENDIENTE": 11},
        "suma_cobros": {"s": 4989239, "f": 249462},
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


def html_count(respuesta, texto):
    return respuesta.content.decode().count(texto)


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

    def cobranza(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse("pagos:cobranza"))

    def test_administrador_y_comite_ven_los_numeros_del_reporte_en_cobranza(self):
        reporte = generar_reporte(self.marzo)
        self.assertEqual((reporte.porcentaje_recaudacion, reporte.deuda_total, len(reporte.unidades_morosas)), (33.3, 120000, 1))
        for usuario in (self.e.administrador, self.e.comite):
            with self.subTest(usuario=usuario):
                respuesta = self.cobranza(usuario)
                self.assertEqual(respuesta.context["cobranza"].periodo, self.marzo)
                self.assertContains(respuesta, "Marzo 2026")
                self.assertContains(respuesta, "33,3 %")
                self.assertContains(respuesta, f"{reverse('gastos:reporte')}?periodo={self.marzo.pk}")
                # Deuda al cierre del período (reporte) y deuda total del condominio (tabla): cada una con su etiqueta.
                self.assertContains(respuesta, "Deuda al cierre del período")
                self.assertContains(respuesta, "Deuda total del condominio")
                self.assertEqual(respuesta.context["cobranza"].deuda_total, 120000)
                self.assertEqual(respuesta.context["deuda_total"], sum(f["deuda"] for f in respuesta.context["filas"]))
                self.assertEqual(respuesta.context["deuda_total"], 120000)
                self.assertContains(respuesta, "$120.000", count=2)
                self.assertEqual(html_count(respuesta, 'class="indicador"'), 3)

    def test_cobranza_sin_periodos_emitidos(self):
        PeriodoGasto.objects.update(estado=PeriodoGasto.Estado.ABIERTO)
        respuesta = self.cobranza(self.e.administrador)
        self.assertContains(respuesta, "Aún no hay gastos comunes emitidos")
        self.assertContains(respuesta, "Deuda total del condominio")
        self.assertNotContains(respuesta, "Recaudación")
        self.assertContains(respuesta, "A101")  # la tabla sigue igual

    def test_inicio_ya_no_trae_la_tarjeta_de_cobranza_pero_si_las_de_unidades(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertNotContains(respuesta, "Recaudación")
        self.assertNotContains(respuesta, "Cobranza de")
        self.assertNotIn("cobranza", respuesta.context)
        self.assertContains(respuesta, "Unidades morosas")

    def test_inicio_sin_periodos_emitidos_avisa_que_faltan_las_tarjetas_de_unidades(self):
        PeriodoGasto.objects.update(estado=PeriodoGasto.Estado.ABIERTO)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertContains(respuesta, "Aún no hay gastos comunes emitidos")
        self.assertNotContains(respuesta, "Unidades morosas")

    def test_conserje_y_residente_no_acceden(self):
        for usuario in (self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario):
                self.assertEqual(self.cobranza(usuario).status_code, 403)
                self.client.force_login(usuario)
                respuesta = self.client.get(reverse("core:inicio"))
                self.assertNotIn("cobranza", respuesta.context)
                self.assertNotContains(respuesta, "Unidades morosas")
                self.assertNotContains(respuesta, "Recaudación")


class TarjetasPorEstadoTest(TestCase):
    """Tarjetas por estado del panel (Issue #79): cantidades, roles, enlaces y aislamiento."""

    def setUp(self):
        self.e = crear_escenario()
        febrero = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=2, estado=PeriodoGasto.Estado.EMITIDO
        )
        self.marzo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=3, estado=PeriodoGasto.Estado.EMITIDO
        )
        # A101 debe febrero y marzo (morosa), A102 solo marzo (con deuda) y B101 pagó (al día).
        DetalleGastoComun.objects.create(periodo=febrero, unidad=self.e.a101, monto=40000, monto_fondo_reserva=0)
        for unidad in (self.e.a101, self.e.a102, self.e.b101):
            cobro = DetalleGastoComun.objects.create(periodo=self.marzo, unidad=unidad, monto=40000, monto_fondo_reserva=0)
            if unidad == self.e.b101:
                Pago.registrar(cobro, monto=40000, registrado_por=self.e.administrador)
        hoy = date.today()
        for estado, cuantos in ((Incidente.Estado.RECIBIDO, 1), (Incidente.Estado.EN_PROCESO, 2), (Incidente.Estado.RESUELTO, 4)):
            for _ in range(cuantos):
                self.incidente(self.e.condominio, estado)
        self.reservar(self.e.quincho, self.e.a101, hoy)
        self.reservar(self.e.quincho, self.e.a102, hoy + timedelta(days=1), hora=time(10))
        self.reservar(self.e.quincho, self.e.b101, hoy + timedelta(days=2), estado=Reserva.Estado.CANCELADA)
        self.reservar(self.e.quincho, self.e.b101, hoy - timedelta(days=1))

    def incidente(self, condominio, estado):
        return Incidente.objects.create(
            condominio=condominio, reportado_por=self.e.residente, categoria=Incidente.Categoria.OTRO,
            titulo="Algo", descripcion="x", estado=estado,
        )

    def reservar(self, espacio, unidad, fecha, hora=time(9), estado=Reserva.Estado.CONFIRMADA):
        return Reserva.objects.create(
            espacio=espacio, unidad=unidad, solicitante=self.e.residente, fecha=fecha,
            hora_inicio=hora, hora_fin=time(hora.hour + 1), estado=estado,
        )

    def tarjetas(self, usuario):
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse("core:inicio"))
        return respuesta, {t["clave"]: t for t in respuesta.context.get("tarjetas", [])}

    def test_cantidades_de_unidades_coinciden_con_el_reporte_y_suman_el_periodo(self):
        reporte = generar_reporte(self.marzo)
        for usuario in (self.e.administrador, self.e.comite):
            with self.subTest(usuario=usuario):
                _, t = self.tarjetas(usuario)
                self.assertEqual(t["moroso"]["cantidad"], len(reporte.unidades_morosas))
                self.assertEqual(t["con-deuda"]["cantidad"], len(reporte.unidades_con_deuda) - len(reporte.unidades_morosas))
                self.assertEqual(t["al-dia"]["cantidad"], len(reporte.filas) - len(reporte.unidades_con_deuda))
                suma = t["al-dia"]["cantidad"] + t["con-deuda"]["cantidad"] + t["moroso"]["cantidad"]
                self.assertEqual(suma, len(reporte.filas))
                self.assertEqual((t["al-dia"]["cantidad"], t["con-deuda"]["cantidad"], t["moroso"]["cantidad"]), (1, 1, 1))

    def test_cantidades_de_incidentes_y_reservas(self):
        _, t = self.tarjetas(self.e.administrador)
        self.assertEqual(t["recibido"]["cantidad"], 1)  # los resueltos no cuentan
        self.assertEqual(t["en-proceso"]["cantidad"], 2)
        self.assertEqual(t["reserva"]["cantidad"], 2)  # hoy y mañana; ni la cancelada ni la pasada
        self.assertEqual(t["reserva"]["frase"], "1 para hoy")

    def test_administrador_y_comite_ven_seis_tarjetas_y_el_conserje_tres(self):
        seis = ["al-dia", "con-deuda", "moroso", "recibido", "en-proceso", "reserva"]
        for usuario in (self.e.administrador, self.e.comite):
            self.assertEqual(list(self.tarjetas(usuario)[1]), seis)
        respuesta, t = self.tarjetas(self.e.conserje)
        self.assertEqual(list(t), ["recibido", "en-proceso", "reserva"])
        self.assertNotContains(respuesta, "Unidades morosas")
        self.assertNotContains(respuesta, "$")
        self.assertContains(respuesta, "row-cols-lg-3")

    def test_residente_sin_tarjetas_por_estado(self):
        respuesta, t = self.tarjetas(self.e.residente)
        self.assertEqual(t, {})
        self.assertNotContains(respuesta, 'class="kpi ')
        self.assertContains(respuesta, "Mi deuda")

    def test_sin_periodo_emitido_no_hay_tarjetas_de_unidades(self):
        PeriodoGasto.objects.update(estado=PeriodoGasto.Estado.ABIERTO)
        respuesta, t = self.tarjetas(self.e.administrador)
        self.assertEqual(list(t), ["recibido", "en-proceso", "reserva"])
        self.assertContains(respuesta, "Aún no hay gastos comunes emitidos")

    def test_cada_tarjeta_enlaza_a_su_url(self):
        respuesta, t = self.tarjetas(self.e.administrador)
        lista = reverse("incidentes:lista")
        reporte = f"{reverse('gastos:reporte')}?periodo={self.marzo.pk}&situacion="
        esperado = {
            "al-dia": reporte + "al_dia", "con-deuda": reporte + "pendiente", "moroso": reporte + "morosa",
            "recibido": f"{lista}?estado=RECIBIDO", "en-proceso": f"{lista}?estado=EN_PROCESO",
            "reserva": reverse("reservas:todas"),
        }
        for clave, url in esperado.items():
            with self.subTest(clave=clave):
                self.assertEqual(t[clave]["url"], url)
                href = url.replace("&", "&amp;")  # el HTML escapa el &
                self.assertContains(respuesta, f'<a class="kpi kpi-{clave}" href="{href}">')
        # Los enlaces de incidentes llevan a una lista que ya filtra por ese estado.
        self.client.force_login(self.e.administrador)
        en_proceso = self.client.get(t["en-proceso"]["url"])
        self.assertEqual(len(en_proceso.context["object_list"]), 2)

    def test_las_tarjetas_de_unidades_abren_el_reporte_filtrado_y_cuadran_con_los_chips(self):
        _, t = self.tarjetas(self.e.administrador)
        for clave in ("al-dia", "con-deuda", "moroso"):
            with self.subTest(clave=clave):
                respuesta = self.client.get(t[clave]["url"])
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(len(respuesta.context["filas"]), t[clave]["cantidad"])
                activos = [c for c in respuesta.context["chips"] if c["activo"]]
                self.assertEqual(len(activos), 1)
                self.assertEqual(activos[0]["cantidad"], t[clave]["cantidad"])

    def test_la_tarjeta_es_un_enlace_con_nombre_y_cantidad(self):
        respuesta, _ = self.tarjetas(self.e.administrador)
        html = respuesta.content.decode()
        self.assertEqual(html.count('<a class="kpi '), 6)
        self.assertIn("Unidades morosas", html)
        self.assertIn('class="kpi-punto" aria-hidden="true"', html)
        self.assertEqual(html.count('class="kpi-lateral" aria-hidden="true"'), 6)  # ícono y flecha son decorativos
        for icono in ("bi-check-circle", "bi-hourglass-split", "bi-exclamation-triangle", "bi-inbox", "bi-wrench", "bi-calendar-event"):
            self.assertIn(icono, html)

    def test_singular_y_plural(self):
        _, t = self.tarjetas(self.e.administrador)
        self.assertEqual((t["moroso"]["cantidad"], t["moroso"]["etiqueta"]), (1, "unidad"))
        self.assertEqual((t["en-proceso"]["cantidad"], t["en-proceso"]["etiqueta"]), (2, "incidentes"))
        self.assertEqual((t["recibido"]["cantidad"], t["recibido"]["etiqueta"]), (1, "incidente"))
        self.assertEqual((t["reserva"]["cantidad"], t["reserva"]["etiqueta"]), (2, "reservas"))
        Reserva.objects.filter(fecha=date.today() + timedelta(days=1)).delete()
        _, t = self.tarjetas(self.e.administrador)
        self.assertEqual((t["reserva"]["etiqueta"], t["reserva"]["frase"]), ("reserva", "1 para hoy"))
        Reserva.objects.all().delete()
        _, t = self.tarjetas(self.e.administrador)
        self.assertEqual((t["reserva"]["cantidad"], t["reserva"]["etiqueta"], t["reserva"]["frase"]), (0, "reservas", "0 para hoy"))

    def test_las_cantidades_no_incluyen_otro_condominio(self):
        ajeno = self.e.ajeno
        for estado in (Incidente.Estado.RECIBIDO, Incidente.Estado.EN_PROCESO):
            for _ in range(3):
                self.incidente(ajeno, estado)
        espacio = EspacioComun.objects.create(condominio=ajeno, nombre="Sala", capacidad=5)
        for _ in range(3):
            self.reservar(espacio, self.e.unidad_ajena, date.today())
        periodo = PeriodoGasto.objects.create(condominio=ajeno, anio=2026, mes=4, estado=PeriodoGasto.Estado.EMITIDO)
        DetalleGastoComun.objects.create(periodo=periodo, unidad=self.e.unidad_ajena, monto=1000, monto_fondo_reserva=0)
        _, t = self.tarjetas(self.e.administrador)
        self.assertEqual([t[c]["cantidad"] for c in ("al-dia", "con-deuda", "moroso")], [1, 1, 1])
        self.assertEqual([t[c]["cantidad"] for c in ("recibido", "en-proceso", "reserva")], [1, 2, 2])

    def test_numero_de_consultas_no_depende_de_los_datos(self):
        """Las unidades salen del reporte ya generado y los incidentes y reservas son una consulta agregada
        cada uno: más datos no suman consultas, y las tarjetas reemplazan a los conteos del resumen."""
        self.client.force_login(self.e.administrador)

        def consultas():
            with CaptureQueriesContext(connection) as c:
                self.client.get(reverse("core:inicio"))
            return c

        consultas()  # la primera visita abre la sesión; se mide desde la segunda
        antes = len(consultas())
        for _ in range(5):
            self.incidente(self.e.condominio, Incidente.Estado.RECIBIDO)
            self.reservar(self.e.quincho, self.e.a101, date.today() + timedelta(days=3), hora=time(12))
        c = consultas()
        self.assertEqual(len(c), antes)
        agrupadas = [q for q in c.captured_queries if "GROUP BY" in q["sql"] and "incidentes_incidente" in q["sql"]]
        self.assertEqual(len(agrupadas), 1)


class FormatoMontoTest(SimpleTestCase):
    """Issue #76: gramática estricta de los montos en pesos."""

    def test_entradas_validas(self):
        for texto, esperado in [
            ("$ 1.250.000", "1250000"), ("$1.250", "1250"), ("1250000", "1250000"), (" 85.000 ", "85000"),
            ("0", "0"), ("999", "999"), ("1.000", "1000"), ("$ 85", "85"),
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(normalizar_monto(texto), esperado)

    def test_entradas_invalidas(self):
        for texto in [
            "1,5", "1.5", "1500.5", "1.25.000", "0.500", "01.000", "-5", "abc", "1 250 000", "", "$", "1.250.00",
            "1250.000.", ".500", "$$5", None, "١٢٣",
        ]:
            with self.subTest(texto=texto):
                self.assertIsNone(normalizar_monto(texto))

    def test_formatear_monto(self):
        for valor, esperado in [(0, "0"), (999, "999"), (1234567, "1.234.567"), (-5000, "-5.000"), (None, "0")]:
            with self.subTest(valor=valor):
                self.assertEqual(formatear_monto(valor), esperado)

    def test_pesos_conserva_su_salida(self):
        """El filtro |pesos da lo mismo que antes de usar formatear_monto."""
        for valor, esperado in [
            (1234567, "$1.234.567"), (-5000, "-$5.000"), (1500.6, "$1.501"), (None, "$0"), ("", "$0"),
            ("abc", "abc"), (0, "$0"), (990, "$990"), ("85000", "$85.000"),
        ]:
            with self.subTest(valor=valor):
                self.assertEqual(pesos(valor), esperado)


class MontoFieldTest(SimpleTestCase):
    def test_limpia_entradas_validas(self):
        campo = MontoField()
        for texto, esperado in [("$ 1.250.000", 1250000), ("1250000", 1250000), (" 85.000 ", 85000)]:
            with self.subTest(texto=texto):
                self.assertEqual(campo.clean(texto), esperado)

    def test_rechaza_entradas_invalidas_con_el_mensaje(self):
        campo = MontoField()
        for texto in ["1,5", "abc", "-5", "1500.5", "0.500", "01.000", "1.25.000"]:
            with self.subTest(texto=texto):
                with self.assertRaises(forms.ValidationError) as error:
                    campo.clean(texto)
                self.assertEqual(error.exception.messages, [MENSAJE_MONTO_INVALIDO])

    def test_obligatorio_y_opcional(self):
        with self.assertRaises(forms.ValidationError):
            MontoField().clean("")
        self.assertIsNone(MontoField(required=False).clean(""))

    def test_respeta_minimo_y_maximo(self):
        with self.assertRaises(forms.ValidationError):
            MontoField(min_value=1).clean("0")
        self.assertEqual(MontoField(min_value=0).clean("0"), 0)
        with self.assertRaises(forms.ValidationError):
            MontoField(max_value=999999999).clean("1.000.000.000")

    def test_widget(self):
        widget = MontoInput()
        self.assertEqual(widget.format_value(1250000), "1.250.000")
        self.assertEqual(widget.format_value("$ 1250000"), "1.250.000")
        self.assertEqual(widget.format_value("1500.5"), "1500.5")  # inválido: tal cual, junto al error
        self.assertIsNone(widget.format_value(None))
        html = widget.render("monto", 450000)
        for atributo in ('inputmode="numeric"', "data-monto", 'type="text"', 'value="450.000"'):
            self.assertIn(atributo, html)


class PrefijoMontoTest(SimpleTestCase):
    class Formulario(forms.Form):
        monto = MontoField(label="Monto")
        nombre = forms.CharField(label="Nombre")

    def dibujar(self, campo):
        return render_to_string("_campo.html", {"campo": self.Formulario()[campo]})

    def test_el_monto_lleva_prefijo_solo(self):
        html = self.dibujar("monto")
        self.assertIn('class="input-group-text" data-prefijo>$', html)

    def test_un_campo_comun_no(self):
        self.assertNotIn("input-group", self.dibujar("nombre"))

    def test_el_prefijo_explicito_manda(self):
        html = render_to_string("_campo.html", {"campo": self.Formulario()["monto"], "prefijo": "UF"})
        self.assertIn("data-prefijo>UF", html)


class ListadosHelperTest(SimpleTestCase):
    """Filtros por GET y chips (Issue #80): valores desconocidos, `page` y los demás parámetros."""

    validos = {"estado": ["A", "B"]}

    def get(self, consulta):
        from django.http import QueryDict
        return QueryDict(consulta)

    def test_valor_desconocido_se_ignora(self):
        from apps.core.listados import leer_opcion
        self.assertEqual(leer_opcion(self.get("estado=A"), "estado", ["A", "B"]), "A")
        self.assertEqual(leer_opcion(self.get("estado=XYZ"), "estado", ["A", "B"]), "")
        self.assertEqual(leer_opcion(self.get(""), "estado", ["A", "B"]), "")

    def chips(self, consulta):
        from apps.core.listados import armar_chips
        return armar_chips(
            self.get(consulta), self.validos, "estado", [("A", "Uno", "recibido"), ("B", "Dos", "resuelto")],
            {"A": 1, "B": 2}, singular="cosa", plural="cosas",
        )

    def test_chips_cantidades_y_activo(self):
        todos, a, b = self.chips("estado=B")
        self.assertEqual((todos["cantidad"], a["cantidad"], b["cantidad"]), (3, 1, 2))
        self.assertEqual((todos["activo"], a["activo"], b["activo"]), (False, False, True))
        self.assertEqual((a["descripcion"], b["descripcion"]), ("1 cosa", "2 cosas"))

    def test_chip_conserva_otros_parametros_y_quita_page(self):
        todos, a, _ = self.chips("estado=B&periodo=5&page=3")
        self.assertEqual(a["url"], "?estado=A&periodo=5")
        self.assertEqual(todos["url"], "?periodo=5")

    def test_valor_desconocido_deja_todos_activo_y_no_se_conserva(self):
        from apps.core.listados import hay_filtros, parametros_de_url
        todos, _, _ = self.chips("estado=XYZ&periodo=5")
        self.assertTrue(todos["activo"])
        self.assertEqual(parametros_de_url(self.get("estado=XYZ&periodo=5&page=2"), self.validos), "periodo=5")
        self.assertFalse(hay_filtros(self.get("estado=XYZ"), self.validos))
        self.assertTrue(hay_filtros(self.get("estado=A"), self.validos))

    def test_limpiar_quita_filtros_y_q_pero_conserva_el_resto(self):
        from apps.core.listados import url_limpiar
        self.assertEqual(url_limpiar(self.get("estado=A&q=x&periodo=5&page=2"), self.validos), "?periodo=5")
        self.assertEqual(url_limpiar(self.get("estado=A"), self.validos), "?")
        self.assertEqual(url_limpiar(self.get("q=perez&periodo=5"), self.validos), "?periodo=5")

    def test_q_cuenta_como_filtro_solo_si_el_listado_declara_busqueda(self):
        """Issue #82: `hay_filtros` cuenta `q` solo con `busqueda=True`; vacío o con espacios no cuenta."""
        from apps.core.listados import hay_filtros
        self.assertFalse(hay_filtros(self.get("q=perez"), self.validos))
        self.assertTrue(hay_filtros(self.get("q=perez"), self.validos, busqueda=True))
        self.assertFalse(hay_filtros(self.get("q=%20%20"), self.validos, busqueda=True))
        self.assertFalse(hay_filtros(self.get(""), self.validos, busqueda=True))

    def test_normalizar_busqueda(self):
        from apps.core.listados import normalizar_busqueda
        self.assertEqual(normalizar_busqueda("  ana   pérez "), "ana pérez")
        self.assertEqual(normalizar_busqueda("a b c d e f g"), "a b c d e")
        self.assertEqual(len(normalizar_busqueda("x" * 300)), 100)
        self.assertEqual(normalizar_busqueda(None), "")


class BusquedaEnOtrosListadosTest(TestCase):
    """Issue #82: un listado que no declara `busqueda` (incidentes) ignora `?q=` y no ofrece «Limpiar filtros»."""

    def test_q_en_incidentes_no_tiene_efecto(self):
        e = crear_escenario()
        Incidente.objects.create(
            condominio=e.condominio, reportado_por=e.residente, categoria=Incidente.Categoria.OTRO,
            titulo="Fuga", descripcion="x",
        )
        self.client.force_login(e.administrador)
        respuesta = self.client.get(reverse("incidentes:lista"), {"q": "nada-que-coincida"})
        self.assertEqual(len(respuesta.context["incidentes"]), 1)
        self.assertFalse(respuesta.context["hay_filtros"])
        self.assertNotContains(respuesta, "Limpiar filtros")


class RespuestaCsvTest(SimpleTestCase):
    """`respuesta_csv` (apps/core/exportar.py): lo que comparten el reporte de morosidad y la cartera."""

    def descargar(self, encabezados, filas):
        from apps.core.exportar import respuesta_csv

        return respuesta_csv("prueba.csv", encabezados, filas)

    def test_lleva_bom_punto_y_coma_y_nombre_de_archivo(self):
        respuesta = self.descargar(["Unidad", "Saldo"], [["A101", 42000], ["A102", 0]])
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(respuesta["Content-Disposition"], 'attachment; filename="prueba.csv"')
        texto = respuesta.content.decode("utf-8")
        self.assertTrue(texto.startswith("\ufeffUnidad;Saldo"))
        self.assertIn("A101;42000", texto)
        self.assertEqual(len(texto.splitlines()), 3)  # encabezado y dos filas

    def test_neutraliza_las_formulas_y_deja_los_numeros(self):
        respuesta = self.descargar(["Nombre", "Monto"], [["=SUMA(1)", -5], ["@cmd", 7], ["Torre A", 1]])
        lineas = respuesta.content.decode("utf-8").splitlines()
        self.assertEqual(lineas[1], "'=SUMA(1);-5")  # el texto con apóstrofo; el número negativo intacto
        self.assertEqual(lineas[2], "'@cmd;7")
        self.assertEqual(lineas[3], "Torre A;1")
