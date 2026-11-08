"""Pruebas del patrón Observer y de las notificaciones (RF10), en el sitio y por correo (Issue #14)."""
from datetime import date
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.comunicados.models import Comunicado
from apps.condominios.models import Residente
from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, Egreso, PeriodoGasto
from apps.gastos.servicios import emitir_periodo
from apps.incidentes.models import Incidente
from apps.pagos.models import Pago

from .models import Notificacion, RecordatorioEnviado
from .observador import Evento, NotificadorCorreo, Observador, Sujeto
from .recordatorios import enviar_recordatorios, tipo_de_aviso


class ObservadorDePrueba(Observador):
    """Observador falso que solo anota los eventos que recibe."""

    def __init__(self):
        self.recibidos = []

    def actualizar(self, evento):
        self.recibidos.append(evento)


class PatronObserverTest(SimpleTestCase):
    def test_el_sujeto_avisa_a_todos_sus_observadores(self):
        class SujetoDePrueba(Sujeto):
            pass

        uno, dos = ObservadorDePrueba(), ObservadorDePrueba()
        SujetoDePrueba.suscribir(uno)
        SujetoDePrueba.suscribir(dos)
        evento = Evento(condominio=None, titulo="t", mensaje="m")
        SujetoDePrueba().notificar(evento)
        self.assertEqual(uno.recibidos, [evento])
        self.assertEqual(dos.recibidos, [evento])

    def test_cada_sujeto_tiene_sus_propios_observadores(self):
        class SujetoA(Sujeto):
            pass

        class SujetoB(Sujeto):
            pass

        observador = ObservadorDePrueba()
        SujetoA.suscribir(observador)
        SujetoB().notificar(Evento(condominio=None, titulo="t", mensaje="m"))
        self.assertEqual(observador.recibidos, [])  # SujetoB no tiene a ese observador

    def test_desuscribir(self):
        class SujetoC(Sujeto):
            pass

        observador = ObservadorDePrueba()
        SujetoC.suscribir(observador)
        SujetoC.desuscribir(observador)
        SujetoC().notificar(Evento(condominio=None, titulo="t", mensaje="m"))
        self.assertEqual(observador.recibidos, [])


class NotificacionVistasTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.n = Notificacion.objects.create(
            usuario=self.e.residente, condominio=self.e.condominio, titulo="Hola", mensaje="m", url="/comunicados/"
        )

    def test_abrir_marca_como_leida_y_redirige(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("notificaciones:abrir", args=[self.n.pk]))
        self.assertRedirects(respuesta, "/comunicados/", fetch_redirect_response=False)
        self.n.refresh_from_db()
        self.assertTrue(self.n.leida)

    def test_no_abre_notificaciones_ajenas(self):
        self.client.force_login(self.e.residente_b)
        self.assertEqual(self.client.get(reverse("notificaciones:abrir", args=[self.n.pk])).status_code, 404)

    def test_no_redirige_a_sitios_externos(self):
        self.n.url = "https://sitio-malicioso.com/"
        self.n.save()
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("notificaciones:abrir", args=[self.n.pk]))
        self.assertRedirects(respuesta, reverse("notificaciones:lista"))

    def test_campana_cuenta_las_no_leidas(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("core:inicio")).context["notificaciones_sin_leer"], 1)

    def test_campana_en_celular_muestra_texto_y_cantidad(self):
        """En el menú del celular: ícono + "Notificaciones" + número; el lector de pantalla oye la cantidad."""
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertContains(respuesta, 'aria-label="Notificaciones, 1 sin leer"')
        self.assertContains(respuesta, '<span class="badge rounded-pill bg-danger ms-1">1</span>', html=True)

    def test_marcar_todas_leidas(self):
        self.client.force_login(self.e.residente)
        self.client.post(reverse("notificaciones:marcar_todas_leidas"))
        self.assertFalse(Notificacion.objects.filter(leida=False).exists())


@override_settings(SITIO_URL="https://condohub.test")
class NotificadorCorreoTest(TestCase):
    """
    Issue #14: el mismo aviso que llega a la campana llega también por correo.

    captureOnCommitCallbacks(execute=True): los correos se envían con
    transaction.on_commit() y, como cada prueba corre dentro de una transacción
    que nunca se confirma, hay que pedirle a Django que ejecute esos envíos.
    """

    def setUp(self):
        self.e = crear_escenario()

    def destinatarios(self):
        return sorted(correo for mensaje in mail.outbox for correo in mensaje.to)

    def publicar_comunicado(self, **campos):
        comunicado = Comunicado(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Corte de agua", contenido="Mañana de 9 a 13 h.",
            **campos,
        )
        with self.captureOnCommitCallbacks(execute=True):
            comunicado.publicar()
        return comunicado

    def test_comunicado_llega_por_correo_a_los_mismos_que_la_campana(self):
        self.publicar_comunicado()
        campana = sorted(Notificacion.objects.values_list("usuario__email", flat=True))
        self.assertEqual(self.destinatarios(), campana)
        self.assertEqual(self.destinatarios(), ["comite@prueba.cl", "residente.b@prueba.cl", "residente@prueba.cl"])

    def test_contenido_del_correo(self):
        comunicado = self.publicar_comunicado()
        correo = next(m for m in mail.outbox if m.to == ["residente@prueba.cl"])
        self.assertEqual(correo.subject, "[CondoHub] Nuevo comunicado")
        self.assertIn("Hola residente:", correo.body)
        self.assertIn("Prueba", correo.body)  # nombre del condominio
        self.assertIn(f"https://condohub.test{comunicado.get_absolute_url()}", correo.body)  # enlace completo
        self.assertIn(f"https://condohub.test{reverse('cuentas:perfil')}", correo.body)  # cómo desactivarlos

    def test_quien_desactivo_los_correos_solo_ve_la_campana(self):
        self.e.residente.recibir_correos = False
        self.e.residente.save()
        self.publicar_comunicado()
        self.assertNotIn("residente@prueba.cl", self.destinatarios())
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.residente).exists())

    def test_cambio_de_estado_de_incidente(self):
        incidente = Incidente.objects.create(
            condominio=self.e.condominio, reportado_por=self.e.residente,
            categoria=Incidente.Categoria.ASEO, titulo="Basura en el pasillo", descripcion="Piso 2",
        )
        with self.captureOnCommitCallbacks(execute=True):
            incidente.cambiar_estado(Incidente.Estado.RESUELTO)
        self.assertEqual(self.destinatarios(), ["residente@prueba.cl"])
        self.assertEqual(mail.outbox[0].subject, "[CondoHub] Tu incidente cambió de estado")

    def test_gastos_comunes_emitidos_y_pago_registrado(self):
        periodo = PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=10)
        Egreso.objects.create(
            periodo=periodo, creado_por=self.e.administrador, monto=100000,
            categoria=Egreso.Categoria.ASEO, descripcion="Aseo", fecha=date(2026, 10, 5),
        )
        with self.captureOnCommitCallbacks(execute=True):
            emitir_periodo(periodo)
        self.assertIn("[CondoHub] Gastos comunes emitidos", [m.subject for m in mail.outbox])

        mail.outbox.clear()
        cobro = periodo.detalles.get(unidad=self.e.a101)
        with self.captureOnCommitCallbacks(execute=True):
            Pago.registrar(cobro, monto=1000, registrado_por=self.e.administrador)
        self.assertEqual(self.destinatarios(), ["residente@prueba.cl"])
        self.assertEqual(mail.outbox[0].subject, "[CondoHub] Registramos tu pago")

    def test_si_la_operacion_se_deshace_no_sale_ningun_correo(self):
        class Falla(Exception):
            pass

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(Falla), transaction.atomic():
                Comunicado(
                    condominio=self.e.condominio, autor=self.e.administrador, titulo="x", contenido="x"
                ).publicar()
                raise Falla  # algo falla después de avisar: la transacción se deshace
        self.assertEqual(mail.outbox, [])

    def test_si_falla_el_servidor_de_correo_lo_demas_sigue(self):
        with mock.patch("apps.notificaciones.observador.get_connection", side_effect=ConnectionError("SMTP caído")):
            with self.assertLogs("apps.notificaciones.observador", level="ERROR"):
                comunicado = self.publicar_comunicado()
        self.assertTrue(Comunicado.objects.filter(pk=comunicado.pk).exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.residente).exists())  # la campana sí avisó

    def test_el_log_no_acepta_saltos_de_linea_del_titulo(self):
        evento = Evento(condominio=self.e.condominio, titulo="Aviso\nINFO falso", mensaje="m", destinatarios=[self.e.residente])
        with mock.patch("apps.notificaciones.observador.get_connection", side_effect=ConnectionError("SMTP caído")):
            with self.assertLogs("apps.notificaciones.observador", level="ERROR") as registro:
                NotificadorCorreo().enviar(evento, [self.e.residente])
        self.assertIn("«Aviso INFO falso»", registro.records[0].getMessage())

    def test_un_correo_por_persona_aunque_venga_repetida(self):
        evento = Evento(condominio=self.e.condominio, titulo="t", mensaje="m", destinatarios=[self.e.residente] * 3)
        with self.captureOnCommitCallbacks(execute=True):
            NotificadorCorreo().actualizar(evento)
        self.assertEqual(self.destinatarios(), ["residente@prueba.cl"])

    def test_la_preferencia_se_cambia_en_mi_perfil(self):
        self.client.force_login(self.e.residente)
        self.assertIn("recibir_correos", self.client.get(reverse("cuentas:perfil")).context["form"].fields)
        # Una casilla desmarcada no se envía en el formulario: así se desactiva.
        self.client.post(reverse("cuentas:perfil"), {"first_name": "Vale", "last_name": "Soto", "rut": "", "telefono": ""})
        self.e.residente.refresh_from_db()
        self.assertFalse(self.e.residente.recibir_correos)
        self.client.post(
            reverse("cuentas:perfil"),
            {"first_name": "Vale", "last_name": "Soto", "rut": "", "telefono": "", "recibir_correos": "on"},
        )
        self.e.residente.refresh_from_db()
        self.assertTrue(self.e.residente.recibir_correos)


# --------------------------------------------------------------------------
# Recordatorios de pago (Issue #57)
# --------------------------------------------------------------------------
class RecordatoriosTest(TestCase):
    """Con fechas simuladas: el período de marzo 2026 vence el 10 de abril 2026."""

    VENCE = date(2026, 4, 10)

    def setUp(self):
        self.e = crear_escenario()
        self.periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=2026, mes=3, estado=PeriodoGasto.Estado.EMITIDO,
            fecha_vencimiento=self.VENCE,
        )
        self.cobro_a101 = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000
        )
        self.cobro_b101 = DetalleGastoComun.objects.create(
            periodo=self.periodo, unidad=self.e.b101, monto=30000, monto_fondo_reserva=1500
        )

    def enviar(self, dia):
        with self.captureOnCommitCallbacks(execute=True):
            return enviar_recordatorios(dia)

    def avisados(self):
        return sorted(Notificacion.objects.values_list("usuario__email", flat=True))

    def test_avisa_3_dias_antes_con_el_monto_y_el_enlace(self):
        enviados = self.enviar(date(2026, 4, 7))
        self.assertEqual(enviados[RecordatorioEnviado.Tipo.ANTES], 2)
        self.assertEqual(self.avisados(), ["residente.b@prueba.cl", "residente@prueba.cl"])
        aviso = Notificacion.objects.get(usuario=self.e.residente)
        self.assertEqual(aviso.titulo, "Tus gastos comunes de Marzo 2026 vencen el 10-04-2026")
        self.assertIn("$42.000", aviso.mensaje)
        self.assertEqual(aviso.url, reverse("pagos:cobro_detalle", args=[self.cobro_a101.pk]))
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["residente.b@prueba.cl", "residente@prueba.cl"])

    def test_avisa_el_dia_siguiente_al_vencimiento(self):
        enviados = self.enviar(date(2026, 4, 11))
        self.assertEqual(enviados[RecordatorioEnviado.Tipo.DESPUES], 2)
        self.assertIn("están vencidos", Notificacion.objects.first().titulo)

    def test_ventanas(self):
        for dia, tipo in [
            (date(2026, 4, 6), None),  # 4 días antes: todavía no
            (date(2026, 4, 7), RecordatorioEnviado.Tipo.ANTES),
            (date(2026, 4, 9), RecordatorioEnviado.Tipo.ANTES),
            (date(2026, 4, 10), None),  # el día del vencimiento no se avisa
            (date(2026, 4, 11), RecordatorioEnviado.Tipo.DESPUES),
            (date(2026, 4, 17), RecordatorioEnviado.Tipo.DESPUES),
            (date(2026, 4, 18), None),  # 8 días después: ya no
        ]:
            with self.subTest(dia=dia):
                self.assertEqual(tipo_de_aviso(self.VENCE, dia), tipo)

    def test_no_repite_el_mismo_aviso(self):
        self.enviar(date(2026, 4, 7))
        self.enviar(date(2026, 4, 7))  # el comando corre dos veces el mismo día
        self.enviar(date(2026, 4, 8))  # y al día siguiente, aún antes del vencimiento
        self.assertEqual(Notificacion.objects.count(), 2)
        self.enviar(date(2026, 4, 11))  # después del vencimiento llega el segundo aviso
        self.assertEqual(Notificacion.objects.count(), 4)
        self.assertEqual(RecordatorioEnviado.objects.count(), 4)

    def test_la_constancia_no_se_repite(self):
        RecordatorioEnviado.objects.create(cobro=self.cobro_a101, usuario=self.e.residente, tipo="ANTES")
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecordatorioEnviado.objects.create(cobro=self.cobro_a101, usuario=self.e.residente, tipo="ANTES")

    def test_no_avisa_a_quien_ya_pago(self):
        Pago.registrar(self.cobro_a101, monto=42000, registrado_por=self.e.administrador)
        Notificacion.objects.all().delete()
        self.enviar(date(2026, 4, 7))
        self.assertEqual(self.avisados(), ["residente.b@prueba.cl"])

    def test_con_pago_parcial_avisa_el_saldo(self):
        Pago.registrar(self.cobro_a101, monto=12000, registrado_por=self.e.administrador)
        Notificacion.objects.all().delete()
        self.enviar(date(2026, 4, 7))
        self.assertIn("$30.000", Notificacion.objects.get(usuario=self.e.residente).mensaje)

    def test_no_avisa_fuera_del_periodo_de_residencia(self):
        Residente.objects.filter(usuario=self.e.residente).update(desde=date(2026, 4, 1))  # llegó después de marzo
        Residente.objects.get(usuario=self.e.residente_b).dar_de_baja()
        self.enviar(date(2026, 4, 7))
        self.assertEqual(self.avisados(), [])

    def test_quien_no_quiere_correos_recibe_solo_la_campana(self):
        self.e.residente.recibir_correos = False
        self.e.residente.save()
        self.enviar(date(2026, 4, 7))
        self.assertIn("residente@prueba.cl", self.avisados())
        self.assertEqual([m.to for m in mail.outbox], [["residente.b@prueba.cl"]])

    def test_no_avisa_periodos_sin_emitir(self):
        self.periodo.estado = PeriodoGasto.Estado.ABIERTO
        self.periodo.save()
        self.assertEqual(sum(self.enviar(date(2026, 4, 7)).values()), 0)

    def test_no_avisa_en_un_condominio_desactivado(self):
        self.e.condominio.activo = False
        self.e.condominio.save()
        self.assertEqual(sum(self.enviar(date(2026, 4, 7)).values()), 0)

    def test_comando_con_fecha_simulada(self):
        salida = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("enviar_recordatorios", fecha="2026-04-07", stdout=salida)
        self.assertIn("Recordatorios del 07-04-2026: 2 antes del vencimiento y 0 después", salida.getvalue())

    def test_comando_rechaza_una_fecha_invalida(self):
        with self.assertRaisesMessage(CommandError, "AAAA-MM-DD"):
            call_command("enviar_recordatorios", fecha="07-04-2026")
