"""Pruebas del estado de cuenta del residente (Issue #3, RF03)."""
import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Membresia, Residente
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto
from apps.gastos.reportes import anotar_pagado, generar_reporte
from apps.gastos.servicios import emitir_periodo
from apps.notificaciones.models import Notificacion

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
