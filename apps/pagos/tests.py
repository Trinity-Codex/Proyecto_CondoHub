"""Pruebas del estado de cuenta del residente (Issue #3, RF03)."""
import datetime
from io import BytesIO

from pypdf import PdfReader
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Membresia, Residente
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.core.templatetags.condohub import pesos
from apps.gastos.models import DetalleGastoComun, Egreso, ItemCobro, PeriodoGasto
from apps.gastos.reportes import anotar_pagado, generar_reporte
from apps.gastos.servicios import emitir_periodo
from apps.notificaciones.models import Notificacion

from .consultas import egresos_para_residente
from .models import Pago

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

    def test_comprobante_descargable_refleja_pago_y_saldo_actual(self):
        cobro = self.cobro(self.oct, self.e.a101)
        pago = Pago.objects.create(detalle=cobro, monto=12345, fecha=datetime.date(2026, 10, 3))
        Pago.objects.create(detalle=cobro, monto=1000)
        url = reverse("pagos:comprobante_pago", args=[pago.pk])
        for anulado, saldo in ((False, "$ 28.655"), (True, "$ 41.000")):
            Pago.objects.filter(pk=pago.pk).update(anulado=anulado)
            for usuario, pagina in (
                (self.e.residente, reverse("pagos:cobro_detalle", args=[cobro.pk])),
                (self.e.administrador, reverse("pagos:cuenta_unidad", args=[cobro.unidad_id])),
            ):
                with self.subTest(usuario=usuario, anulado=anulado):
                    self.client.force_login(usuario)
                    self.assertContains(self.client.get(pagina), url)
                    respuesta = self.client.get(url)
                    self.assertEqual(respuesta["Content-Type"], "application/pdf")
                    self.assertIn(f'attachment; filename="comprobante-pago-{pago.pk}.pdf"',
                                  respuesta["Content-Disposition"])
                    self.assertIn("no-store", respuesta["Cache-Control"])
                    pdf = PdfReader(BytesIO(respuesta.content))
                    texto = " ".join(" ".join(p.extract_text() for p in pdf.pages).split())
                    for dato in (f"Pago N° {pago.pk}", "03-10-2026", "$ 12.345", "Transferencia",
                                 str(cobro.periodo), saldo):
                        self.assertIn(dato, texto)
                    self.assertEqual("Anulado" in texto, anulado)

    def test_comprobante_limita_unidad_periodo_condominio_y_rol(self):
        cobro = self.cobro(self.oct, self.e.a101)
        pago = Pago.objects.create(detalle=cobro, monto=2000)
        url = reverse("pagos:comprobante_pago", args=[pago.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        Residente.objects.filter(usuario=self.e.residente).update(desde=datetime.date(2026, 11, 1))
        for usuario, estado in ((self.e.residente, 404), (self.e.residente_b, 404),
                                (self.e.residente_ajeno, 404), (self.e.comite, 403), (self.e.conserje, 403)):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(url).status_code, estado)
        otro = self.e.ajeno
        periodo = PeriodoGasto.objects.create(condominio=otro, anio=2026, mes=10, estado="EMITIDO")
        ajeno = Pago.objects.create(detalle=self.cobro(periodo, self.e.unidad_ajena), monto=1000)
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(reverse("pagos:comprobante_pago", args=[ajeno.pk])).status_code, 404)

    def test_aviso_pdf_cuadra_con_abonos_y_protege_egresos(self):
        self.cobro(self.sep, self.e.a101, monto=3000, fondo=0)
        cobro = self.cobro(self.oct, self.e.a101, monto=48000, fondo=2000)
        Pago.objects.create(detalle=cobro, monto=7010, fecha=datetime.date(2026, 10, 3))
        Pago.objects.create(detalle=cobro, monto=100, anulado=True)
        Egreso.objects.create(periodo=self.oct, categoria=Egreso.Categoria.REMUNERACIONES,
                              descripcion="Nombre confidencial", monto=1000, creado_por=self.e.administrador)
        url = reverse("pagos:aviso_cobro", args=[cobro.pk])
        for usuario in (self.e.residente, self.e.administrador):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta["Content-Disposition"].startswith("attachment;"))
                lector = PdfReader(BytesIO(respuesta.content))
                texto = " ".join(" ".join(p.extract_text() for p in lector.pages).split())
                for fragmento in ("$ 45.990", "$ 42.990", "$ 7.010", "$ 3.000",
                                  "Remuneraciones del personal", "Documento de demostración"):
                    self.assertIn(fragmento, texto)
                self.assertNotIn("Nombre confidencial", texto)

    def test_aviso_respeta_residencia_condominio_estado_y_rol(self):
        propio = self.cobro(self.oct, self.e.a101)
        ajeno = self.cobro(self.oct, self.e.b101)
        antiguo = self.cobro(self.sep, self.e.a101)
        abierto = self.cobro(self.nov, self.e.a101)
        Residente.objects.filter(usuario=self.e.residente).update(desde=datetime.date(2026, 10, 1))
        self.client.force_login(self.e.residente)
        for cobro in (ajeno, antiguo, abierto):
            self.assertEqual(self.client.get(reverse("pagos:aviso_cobro", args=[cobro.pk])).status_code, 404)
        self.client.force_login(self.e.residente_ajeno)
        self.assertEqual(self.client.get(reverse("pagos:aviso_cobro", args=[propio.pk])).status_code, 404)
        self.client.force_login(self.e.comite)
        self.assertEqual(self.client.get(reverse("pagos:aviso_cobro", args=[propio.pk])).status_code, 403)

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
        from apps.gastos.fondo import registrar_movimiento
        registrar_movimiento(self.e.condominio, tipo="INICIAL", monto=0,
            fecha=datetime.date(2026, 11, 1), descripcion="Apertura ficticia del legado de prueba")
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


class EgresosParaResidenteTest(TestCase):
    """Issue #115 (RQ-09): el residente ve los egresos agrupados por categoría, sin sueldos ni descripciones libres."""

    SUELDO = "Sueldo conserje (jornada completa)"
    CLASE_FILA = 'class="list-group-item d-flex flex-wrap justify-content-between gap-3"'

    def fila(self, nombre, subtotal):
        """HTML de una fila de egresos tal como la pinta pagos/detalle.html."""
        return f'<li {self.CLASE_FILA}><span>{nombre}</span><span class="text-nowrap">{subtotal}</span></li>'

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=10, estado=PeriodoGasto.Estado.EMITIDO
        )
        # Dos remuneraciones, dos egresos de aseo y uno de consumos: los sueldos deben sumarse en una línea.
        for categoria, descripcion, monto in (
            ("REMUNERACIONES", self.SUELDO, 650000),
            ("REMUNERACIONES", "Sueldo personal de aseo", 520000),
            ("ASEO", "Insumos de limpieza Casa Pérez", 80000),
            ("ASEO", "Aseo de áreas comunes", 20000),
            ("CONSUMOS", "Cuenta de luz octubre", 300000),
        ):
            Egreso.objects.create(
                periodo=self.periodo, categoria=categoria, descripcion=descripcion, monto=monto,
                creado_por=self.e.administrador,
            )
        self.cobro = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000
        )
        self.url = reverse("pagos:cobro_detalle", args=[self.cobro.pk])

    def test_el_residente_no_ve_sueldos_ni_descripciones_libres(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        prohibidos = (self.SUELDO, "Sueldo personal de aseo", "Casa Pérez", "Cuenta de luz octubre", "650.000")
        for texto in prohibidos:
            self.assertNotContains(respuesta, texto)

    def test_el_residente_ve_las_remuneraciones_en_una_sola_linea(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(self.url)
        # Se afirma la fila completa (nombre + subtotal juntos), no textos sueltos que podrían estar en otra parte.
        html = respuesta.content.decode()
        self.assertInHTML(self.fila("Remuneraciones del personal", "$1.170.000"), html)  # 650.000 + 520.000
        self.assertInHTML(self.fila("Aseo", "$100.000"), html)  # 80.000 + 20.000
        self.assertContains(respuesta, "Remuneraciones del personal", count=1)
        # Una fila por categoría (remuneraciones, consumos, aseo): ningún egreso suelto.
        self.assertEqual(len(respuesta.context["egresos"]), 3)

    def test_una_categoria_fuera_de_las_opciones_no_da_500(self):
        """Un dato antiguo o cargado sin validar se muestra con su valor crudo en vez de romper la página."""
        Egreso.objects.filter(periodo=self.periodo, categoria="OTROS").delete()
        egreso = Egreso.objects.create(
            periodo=self.periodo, categoria="OTROS", descripcion="Dato antiguo", monto=7000,
            creado_por=self.e.administrador,
        )
        # update() salta la validación de choices, como un dato cargado por fuera del formulario.
        Egreso.objects.filter(pk=egreso.pk).update(categoria="LEGADO")
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertInHTML(self.fila("LEGADO", "$7.000"), respuesta.content.decode())
        self.assertNotContains(respuesta, "Dato antiguo")

    def test_un_periodo_con_solo_remuneraciones_muestra_la_linea_agrupada(self):
        """
        Riesgo aceptado por el equipo (design.md «Riesgo conocido»): con un único egreso de remuneraciones,
        la línea agrupada deja ver ese monto. Lo que nunca sale es la descripción libre del egreso.
        """
        solo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=11, estado=PeriodoGasto.Estado.EMITIDO
        )
        Egreso.objects.create(
            periodo=solo, categoria="REMUNERACIONES", descripcion="Sueldo de Juan Soto", monto=480000,
            creado_por=self.e.administrador,
        )
        cobro = DetalleGastoComun.objects.create(periodo=solo, unidad=self.e.a101, monto=10000, monto_fondo_reserva=0)
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[cobro.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertInHTML(self.fila("Remuneraciones del personal", "$480.000"), respuesta.content.decode())
        self.assertEqual(len(respuesta.context["egresos"]), 1)
        self.assertNotContains(respuesta, "Sueldo de Juan Soto")
        self.assertEqual(respuesta.context["total_egresos"], 480000)

    def test_los_subtotales_cuadran_con_el_total_del_periodo(self):
        lineas = egresos_para_residente(self.periodo)
        self.assertEqual(sum(linea["subtotal"] for linea in lineas), self.periodo.total_egresos())
        self.assertEqual(
            [(linea["categoria"], linea["subtotal"]) for linea in lineas],
            [
                ("Remuneraciones del personal", 1170000),
                ("Consumos básicos (luz, agua, gas)", 300000),
                ("Aseo", 100000),
            ],
        )
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["egresos"], lineas)
        self.assertEqual(respuesta.context["total_egresos"], self.periodo.total_egresos())

    def test_periodo_sin_egresos_da_lista_vacia(self):
        vacio = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=9)
        self.assertEqual(egresos_para_residente(vacio), [])

    def test_residente_de_otro_condominio_no_ve_el_cobro(self):
        self.client.force_login(self.e.residente_ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_residente_de_otra_unidad_no_ve_el_cobro(self):
        self.client.force_login(self.e.residente_b)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_respeta_el_filtro_de_residencia(self):
        """#46: quien llegó después del período no ve el cobro ni sus egresos, aunque viva en la unidad."""
        recien_llegado = crear_usuario("nuevo@prueba.cl")
        Residente.objects.create(usuario=recien_llegado, unidad=self.e.a101, desde=datetime.date(2026, 11, 1))
        self.client.force_login(recien_llegado)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_el_residente_no_entra_al_detalle_completo_de_gastos(self):
        url = reverse("gastos:periodo_detalle", args=[self.periodo.pk])
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotContains(respuesta, self.SUELDO, status_code=403)

    def test_administrador_y_comite_conservan_el_detalle_completo(self):
        url = reverse("gastos:periodo_detalle", args=[self.periodo.pk])
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertContains(respuesta, self.SUELDO)


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

    def test_registrar_pago_deja_auditoria_con_el_minimo_de_datos(self):
        """#27 (6.1): crear el pago audita CREAR con actor, condominio y solo monto y medio."""
        self.pagar(10000, observacion="dato privado")
        pago = self.cobro.pagos.get()
        registro = RegistroAuditoria.objects.get()
        self.assertEqual(registro.accion, "crear")
        self.assertEqual(registro.objeto_tipo, "pago")
        self.assertEqual(registro.objeto_id, str(pago.pk))
        self.assertEqual(registro.usuario_id, self.e.administrador.pk)
        self.assertEqual(registro.condominio_id, self.e.condominio.pk)
        self.assertIsNone(registro.antes)
        self.assertEqual(registro.despues, {"monto": 10000, "medio": "TRANSFERENCIA"})

    def test_si_falla_la_auditoria_se_revierten_el_pago_y_el_estado_del_cobro(self):
        with mock.patch("apps.pagos.models.registrar", side_effect=RuntimeError("falla controlada")):
            with self.assertRaises(RuntimeError):
                Pago.registrar(self.cobro, 42000, registrado_por=self.e.administrador)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PENDIENTE)
        self.assertEqual(Pago.objects.count(), 0)
        self.assertEqual(RegistroAuditoria.objects.count(), 0)

    def test_si_falla_una_etapa_posterior_se_revierte_tambien_la_auditoria(self):
        with mock.patch.object(Pago, "notificar", side_effect=RuntimeError("falla controlada")):
            with self.assertRaises(RuntimeError):
                Pago.registrar(self.cobro, 42000, registrado_por=self.e.administrador)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PENDIENTE)
        self.assertEqual(Pago.objects.count(), 0)
        self.assertEqual(RegistroAuditoria.objects.count(), 0)

    def test_monto_con_puntos_y_signo(self):
        """Issue #76: «$ 10.000» registra 10000 y el saldo sigue mandando."""
        self.pagar("$ 10.000")
        self.assertEqual(self.cobro.pagos.get().monto, 10000)

    def test_monto_con_puntos_sobre_el_saldo_se_rechaza(self):
        respuesta = self.pagar("42.001")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("monto", respuesta.context["form"].errors)
        self.assertContains(respuesta, "No puede superar el saldo pendiente ($42.000)")
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_monto_invalido_se_rechaza(self):
        for texto in ["1,5", "0", "0.500", "-5"]:
            self.assertIn("monto", self.pagar(texto).context["form"].errors, texto)
        self.assertEqual(self.cobro.pagos.count(), 0)

    def test_el_formulario_sugiere_el_saldo_con_puntos(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(self.url), 'value="42.000"')

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

    def test_no_avisa_a_quien_llego_despues_del_periodo(self):
        # Llegó el 1 de noviembre; el cobro es de octubre: no lo ve, así que no debe recibir el aviso
        # (si lo recibiera, el enlace le daría 404).
        tarde = crear_usuario("tarde@prueba.cl")
        Residente.objects.create(usuario=tarde, unidad=self.e.a101, desde=datetime.date(2026, 11, 1))
        self.pagar(42000)
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.residente, titulo="Registramos tu pago").exists())
        self.assertFalse(Notificacion.objects.filter(usuario=tarde, titulo="Registramos tu pago").exists())

    def test_no_avisa_a_quien_ya_fue_dado_de_baja(self):
        # Vivió en la unidad hasta fines de septiembre: el cobro de octubre ya no le corresponde.
        baja = crear_usuario("baja@prueba.cl")
        Residente.objects.create(
            usuario=baja, unidad=self.e.a101, desde=datetime.date(2020, 1, 1),
            hasta=datetime.date(2026, 9, 30), activo=False,
        )
        self.pagar(42000)
        self.assertFalse(Notificacion.objects.filter(usuario=baja, titulo="Registramos tu pago").exists())

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


# Motivo de ejemplo que comparten la anulación y sus aserciones.
MOTIVO_ANULACION = "Se registró en la unidad equivocada"


class AnularPagoTest(TestCase):
    """Issue #53: el administrador anula un pago con motivo; el pago queda marcado y el cobro recalcula."""

    AVISO = "Anulamos un pago"

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=10, estado=PeriodoGasto.Estado.EMITIDO
        )
        # Cobro de A101 por $42.000, pagado completo con un solo pago.
        self.cobro = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000
        )
        self.pago = Pago.registrar(self.cobro, monto=42000, registrado_por=self.e.administrador)
        self.url = reverse("pagos:anular_pago", args=[self.pago.pk])

    def anular(self, motivo=MOTIVO_ANULACION, usuario=None):
        self.client.force_login(usuario or self.e.administrador)
        return self.client.post(self.url, {"motivo": motivo})

    def assertSigueVigente(self):
        self.pago.refresh_from_db()
        self.cobro.refresh_from_db()
        self.assertFalse(self.pago.anulado)
        self.assertEqual(self.cobro.estado, Estado.PAGADO)

    def test_anular_el_unico_pago_reabre_el_cobro(self):
        respuesta = self.anular()
        self.assertRedirects(respuesta, reverse("pagos:cuenta_unidad", args=[self.e.a101.pk]))
        self.pago.refresh_from_db()
        self.cobro.refresh_from_db()
        self.assertTrue(self.pago.anulado)
        self.assertEqual(self.pago.motivo_anulacion, MOTIVO_ANULACION)
        self.assertEqual(self.pago.anulado_por, self.e.administrador)
        self.assertIsNotNone(self.pago.anulado_en)
        self.assertEqual(self.cobro.estado, Estado.PENDIENTE)
        # El pago no se borra: sigue en la base, solo deja de contar.
        self.assertEqual(Pago.objects.filter(pk=self.pago.pk).count(), 1)
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("pagos:estado_cuenta")).context["total_adeudado"], 42000)

    def test_la_anulacion_queda_en_la_auditoria(self):
        self.anular()
        registro = RegistroAuditoria.objects.get(accion="anular")
        self.assertEqual((registro.objeto_tipo, registro.objeto_id), ("pago", str(self.pago.pk)))
        self.assertEqual(registro.usuario_id, self.e.administrador.pk)
        self.assertEqual(registro.condominio_id, self.e.condominio.pk)
        self.assertEqual(registro.despues["motivo_anulacion"], MOTIVO_ANULACION)

    def test_avisa_solo_al_residente_que_ve_el_cobro(self):
        # Llegó a A101 en noviembre: el cobro de octubre no es suyo (contrato C2, #46).
        recien_llegado = crear_usuario("nuevo@prueba.cl")
        Residente.objects.create(usuario=recien_llegado, unidad=self.e.a101, desde=datetime.date(2026, 11, 1))
        self.anular("Pago duplicado, a, b")
        aviso = Notificacion.objects.get(usuario=self.e.residente, titulo=self.AVISO)
        self.assertEqual(aviso.url, reverse("pagos:cobro_detalle", args=[self.cobro.pk]))
        # Las comas del motivo se respetan; solo el monto lleva punto de miles.
        self.assertIn("$42.000", aviso.mensaje)
        self.assertIn("Motivo: Pago duplicado, a, b", aviso.mensaje)
        self.assertFalse(Notificacion.objects.filter(usuario=recien_llegado, titulo=self.AVISO).exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.e.residente_b, titulo=self.AVISO).exists())

    def test_el_motivo_es_obligatorio(self):
        for motivo in ("", "   "):
            respuesta = self.anular(motivo)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn("motivo", respuesta.context["form"].errors)
        self.assertSigueVigente()
        self.assertFalse(RegistroAuditoria.objects.filter(accion="anular").exists())

    def test_el_modelo_tambien_exige_el_motivo(self):
        with self.assertRaises(ValidationError):
            self.pago.anular("  ", anulado_por=self.e.administrador)
        self.assertSigueVigente()

    def test_el_modelo_rechaza_un_motivo_de_mas_de_200_caracteres(self):
        # La columna es de 200: sin esta validación, MySQL estricto respondería 500.
        with self.assertRaises(ValidationError):
            self.pago.anular("x" * 201, anulado_por=self.e.administrador)
        self.assertSigueVigente()

    def test_comite_residente_y_conserje_reciben_403(self):
        for usuario in (self.e.comite, self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.anular(usuario=usuario).status_code, 403)
        self.assertSigueVigente()

    def test_un_pago_de_otro_condominio_da_404(self):
        admin_ajeno = crear_usuario("admin.ajeno@prueba.cl")
        Membresia.objects.create(usuario=admin_ajeno, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        self.client.force_login(admin_ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.anular(usuario=admin_ajeno).status_code, 404)
        self.assertSigueVigente()

    def test_un_pago_ya_anulado_no_se_vuelve_a_anular(self):
        self.anular()
        self.assertEqual(self.anular("Otra vez").status_code, 404)
        with self.assertRaises(ValidationError):
            Pago.objects.get(pk=self.pago.pk).anular("Otra vez", anulado_por=self.e.administrador)
        self.assertEqual(RegistroAuditoria.objects.filter(accion="anular").count(), 1)

    def test_anular_un_abono_parcial_deja_el_cobro_pendiente_con_el_saldo_completo(self):
        self.anular()
        abono = Pago.registrar(self.cobro, monto=10000)
        abono.anular("Monto mal digitado", anulado_por=self.e.administrador)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PENDIENTE)
        self.client.force_login(self.e.residente)
        detalle = self.client.get(reverse("pagos:cobro_detalle", args=[self.cobro.pk]))
        self.assertEqual((detalle.context["pagado"], detalle.context["saldo"]), (0, 42000))
        self.assertContains(detalle, "Monto mal digitado")  # el residente ve por qué subió su saldo

    def test_las_sumas_ignoran_los_pagos_anulados(self):
        self.anular()
        self.assertEqual(list(Pago.objects.vigentes()), [])
        self.assertEqual(Pago.objects.count(), 1)  # el manager por defecto sigue viendo todos
        # El saldo del nuevo pago se calcula sin el anulado: se acepta pagar el total otra vez.
        Pago.registrar(self.cobro, monto=42000)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, Estado.PAGADO)
        self.assertEqual(sum(p.monto for p in Pago.objects.vigentes()), 42000)

    def test_el_reporte_de_morosidad_cuadra_con_mi_cuenta_tras_anular(self):
        self.anular()
        Pago.registrar(self.cobro, monto=5000)
        cobro = anotar_pagado(DetalleGastoComun.objects.filter(pk=self.cobro.pk)).get()
        self.assertEqual(cobro.pagado, 5000)
        (fila,) = [f for f in generar_reporte(self.periodo).filas if f.unidad == self.e.a101]
        self.client.force_login(self.e.residente)
        mi_cuenta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertEqual(fila.saldo, 37000)
        self.assertEqual(mi_cuenta.context["total_adeudado"], fila.saldo)
        self.assertEqual(self.client.get(reverse("core:inicio")).context["mi_deuda"], fila.saldo)

    def test_el_panel_admin_es_solo_de_consulta(self):
        """Editar en /admin/ se saltaría el saldo, el motivo, la auditoría, el aviso y el recálculo del cobro."""
        superusuario = crear_usuario("super@prueba.cl", is_staff=True, is_superuser=True)
        self.client.force_login(superusuario)
        url = reverse("admin:pagos_pago_change", args=[self.pago.pk])
        self.assertNotContains(self.client.get(url), 'name="anulado"')
        datos = {
            "detalle": self.cobro.pk, "fecha": self.pago.fecha.isoformat(), "monto": 42000,
            "medio": "TRANSFERENCIA", "observacion": "", "registrado_por": "",
            "anulado": "on", "motivo_anulacion": "Desde el admin",
        }
        # Ni siquiera un superusuario puede guardar ni borrar: el pago queda igual.
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        borrar = reverse("admin:pagos_pago_delete", args=[self.pago.pk])
        self.assertEqual(self.client.post(borrar, {"post": "yes"}).status_code, 403)
        self.assertSigueVigente()
        self.assertEqual(self.pago.motivo_anulacion, "")

    def test_la_cuenta_muestra_el_pago_anulado_y_el_boton_solo_al_administrador(self):
        cuenta = reverse("pagos:cuenta_unidad", args=[self.e.a101.pk])
        self.client.force_login(self.e.comite)
        self.assertNotContains(self.client.get(cuenta), self.url)
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(cuenta), self.url)
        self.anular()
        respuesta = self.client.get(cuenta)
        self.assertNotContains(respuesta, self.url)  # ya no se ofrece anularlo de nuevo
        self.assertContains(respuesta, 'class="insignia insignia-con-deuda">Anulado')
        self.assertEqual(respuesta.context["total_adeudado"], 42000)


class DesgloseItemsDeCobroTest(TestCase):
    """
    RQ-02 parte 2 (#117): el residente ve cada ítem de cobro de SU cobro como una línea separada
    en el detalle, el estado de cuenta y el aviso PDF. Nunca ve la multa de otra unidad.
    """

    def setUp(self):
        from apps.gastos.tests_items import crear_item, periodo_con_egreso

        self.crear_item, self.periodo_con_egreso = crear_item, periodo_con_egreso
        self.e = crear_escenario()  # A101 (0,4), A102 (0,3), B101 (0,3)
        self.periodo = periodo_con_egreso(self.e.condominio, self.e.administrador)
        crear_item(self.periodo, self.e.administrador, monto=30000, nombre="Cuota extraordinaria fachada",
                   modo=ItemCobro.Modo.PRORRATEO)
        crear_item(self.periodo, self.e.administrador, monto=25000, nombre="Multa A101 ruidos",
                   unidades=[self.e.a101])
        crear_item(self.periodo, self.e.administrador, monto=15000, nombre="Multa B101 mascotas",
                   unidades=[self.e.b101])
        emitir_periodo(self.periodo, usuario=self.e.administrador)
        self.cobro_a101 = DetalleGastoComun.objects.get(periodo=self.periodo, unidad=self.e.a101)
        self.cobro_b101 = DetalleGastoComun.objects.get(periodo=self.periodo, unidad=self.e.b101)

    def test_detalle_muestra_sus_lineas_y_cuadra_con_el_total(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[self.cobro_a101.pk]))
        self.assertEqual(respuesta.status_code, 200)
        cobro = respuesta.context["cobro"]
        lineas = {linea.nombre: linea.monto for linea in cobro.lineas.all()}
        # A101 tiene alícuota 0,4: le tocan $12.000 de la cuota de $30.000, más su multa.
        self.assertEqual(lineas, {"Cuota extraordinaria fachada": 12000, "Multa A101 ruidos": 25000})
        self.assertEqual(cobro.monto + cobro.monto_fondo_reserva + sum(lineas.values()), cobro.total)
        self.assertContains(respuesta, "Cuota extraordinaria fachada")
        self.assertContains(respuesta, pesos(25000))
        self.assertNotContains(respuesta, "Multa B101 mascotas")

    def test_estado_de_cuenta_muestra_la_columna_de_items(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("pagos:estado_cuenta"))
        self.assertContains(respuesta, ">Ítems</th>")
        self.assertEqual(self.cobro_a101.monto_items, 37000)
        celda = f'<td class="text-end text-nowrap d-none d-md-table-cell">{pesos(37000)}</td>'
        self.assertContains(respuesta, celda, html=True)

    def test_aviso_pdf_lista_cada_linea_de_su_unidad(self):
        url = reverse("pagos:aviso_cobro", args=[self.cobro_a101.pk])
        for usuario in (self.e.residente, self.e.administrador):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                texto = " ".join(" ".join(p.extract_text() for p in PdfReader(BytesIO(respuesta.content)).pages).split())
                for fragmento in ("Cuota extraordinaria fachada $ 12.000", "Multa A101 ruidos $ 25.000",
                                  "Intereses por mora $ 0"):
                    self.assertIn(fragmento, texto)
                self.assertNotIn("Multa B101", texto)
                self.assertNotIn("Ítems adicionales", texto)

    def test_cobro_de_otra_unidad_o_condominio_da_404(self):
        self.client.force_login(self.e.residente)
        for nombre in ("pagos:cobro_detalle", "pagos:aviso_cobro"):
            with self.subTest(ruta=nombre):
                self.assertEqual(self.client.get(reverse(nombre, args=[self.cobro_b101.pk])).status_code, 404)
        self.client.force_login(self.e.residente_ajeno)
        for nombre in ("pagos:cobro_detalle", "pagos:aviso_cobro"):
            with self.subTest(ruta=nombre, usuario="ajeno"):
                self.assertEqual(self.client.get(reverse(nombre, args=[self.cobro_a101.pk])).status_code, 404)

    def test_residente_b_ve_su_multa_y_no_la_ajena(self):
        self.client.force_login(self.e.residente_b)
        respuesta = self.client.get(reverse("pagos:cobro_detalle", args=[self.cobro_b101.pk]))
        self.assertContains(respuesta, "Multa B101 mascotas")
        self.assertNotContains(respuesta, "Multa A101 ruidos")

    def test_la_demo_de_render_permite_el_mantenedor_de_items(self):
        from apps.core.middleware_demo import es_escritura_bloqueada

        for ruta in ("gastos:item_nuevo", "gastos:item_editar", "gastos:item_eliminar"):
            with self.subTest(ruta=ruta):
                self.assertFalse(es_escritura_bloqueada("POST", ruta))
        self.assertTrue(es_escritura_bloqueada("POST", "gastos:periodo_emitir"))
