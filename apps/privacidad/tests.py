"""Pruebas de privacidad (Issue #51, Ley 21.719): aviso, solicitudes del titular y descarga de mis datos."""
import json
from datetime import date

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Residente
from apps.core.pruebas import crear_escenario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.notificaciones.models import Notificacion
from apps.pagos.models import Pago

from .models import SolicitudTitular


class AvisoPrivacidadTest(TestCase):
    def setUp(self):
        self.url = reverse("privacidad:aviso")

    def test_se_lee_sin_iniciar_sesion(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "<h1", count=1)
        self.assertContains(respuesta, "Aviso de privacidad")

    def test_todos_los_roles_lo_ven(self):
        e = crear_escenario()
        for usuario in (e.administrador, e.comite, e.conserje, e.residente):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_el_pie_de_pagina_tiene_el_enlace(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, f'href="{self.url}"')

    def test_el_inicio_de_sesion_lo_enlaza(self):
        self.assertContains(self.client.get(reverse("cuentas:iniciar_sesion")), f'href="{self.url}"', count=2)  # texto y pie

    def test_contiene_cada_seccion_y_la_advertencia_de_demostracion(self):
        respuesta = self.client.get(self.url)
        for texto in (
            "Instancia de demostración", "Responsable:", "Encargado:", "Qué datos se tratan y para qué",
            "Por cuánto tiempo se conservan", "acceso", "rectificación", "supresión", "oponerte",
            "Agencia de Protección de Datos Personales",
        ):
            with self.subTest(texto=texto):
                self.assertContains(respuesta, texto)

    def test_sin_condominio_activo_no_ofrece_mis_solicitudes(self):
        e = crear_escenario()
        sin_rol = type(e.residente).objects.create_user(email="sin.rol@prueba.cl", password="x")
        self.client.force_login(sin_rol)
        respuesta = self.client.get(self.url)
        self.assertNotContains(respuesta, reverse("privacidad:mis_solicitudes"))
        self.assertContains(respuesta, reverse("privacidad:descargar"))

    def test_no_muestra_datos_de_ningun_condominio(self):
        e = crear_escenario()
        self.client.force_login(e.residente)
        self.assertNotContains(self.client.get(self.url), e.condominio.direccion)


class SolicitudModeloTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.solicitud = SolicitudTitular(
            usuario=self.e.residente, condominio=self.e.condominio, tipo=SolicitudTitular.Tipo.ACCESO, detalle="x"
        )

    def test_presentar_queda_pendiente_y_avisa_a_los_administradores(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.solicitud.presentar()
        self.assertTrue(self.solicitud.esta_pendiente)
        avisados = set(Notificacion.objects.values_list("usuario__email", flat=True))
        self.assertEqual(avisados, {"admin@prueba.cl"})
        self.assertEqual([m.to for m in mail.outbox], [["admin@prueba.cl"]])

    def test_cerrar_guarda_respuesta_fecha_y_avisa_a_la_persona(self):
        self.solicitud.presentar()
        Notificacion.objects.all().delete()
        self.solicitud.cerrar("Listo.", por=self.e.administrador)
        self.solicitud.refresh_from_db()
        self.assertEqual(
            (self.solicitud.estado, self.solicitud.respuesta, self.solicitud.cerrada_por),
            (SolicitudTitular.Estado.CERRADA, "Listo.", self.e.administrador),
        )
        self.assertIsNotNone(self.solicitud.cerrada)
        self.assertEqual(list(Notificacion.objects.values_list("usuario__email", flat=True)), ["residente@prueba.cl"])

    def test_no_se_cierra_dos_veces(self):
        self.solicitud.presentar()
        self.solicitud.cerrar("Listo.", por=self.e.administrador)
        with self.assertRaises(ValueError):
            self.solicitud.cerrar("Otra vez.", por=self.e.administrador)

    def test_dos_administradores_a_la_vez_no_se_pisan(self):
        # Cada uno abrió la solicitud cuando estaba pendiente; el segundo responde después.
        self.solicitud.presentar()
        copia = SolicitudTitular.objects.get(pk=self.solicitud.pk)
        self.solicitud.cerrar("Primera.", por=self.e.administrador)
        with self.assertRaises(ValueError):
            copia.cerrar("Segunda.", por=self.e.administrador)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.respuesta, "Primera.")

    def test_el_nombre_corto_del_tipo(self):
        self.assertEqual(self.solicitud.tipo_corto, "Acceso")


class SolicitudesTitularTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def presentar(self, usuario, tipo=SolicitudTitular.Tipo.RECTIFICACION, detalle="Mi teléfono cambió."):
        self.client.force_login(usuario)
        return self.client.post(reverse("privacidad:solicitud_nueva"), {"tipo": tipo, "detalle": detalle})

    def solicitud_de(self, usuario, condominio=None):
        return SolicitudTitular.objects.create(
            usuario=usuario, condominio=condominio or self.e.condominio, tipo=SolicitudTitular.Tipo.ACCESO, detalle="x"
        )

    def test_un_residente_presenta_en_su_condominio_activo(self):
        respuesta = self.presentar(self.e.residente)
        self.assertRedirects(respuesta, reverse("privacidad:mis_solicitudes"))
        solicitud = SolicitudTitular.objects.get()
        self.assertEqual((solicitud.usuario, solicitud.condominio), (self.e.residente, self.e.condominio))
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.administrador).exists())

    def test_el_detalle_es_obligatorio(self):
        respuesta = self.presentar(self.e.residente, detalle="")
        self.assertIn("detalle", respuesta.context["form"].errors)

    def test_cualquier_miembro_puede_presentar(self):
        for usuario in (self.e.comite, self.e.conserje):
            with self.subTest(usuario=usuario.email):
                self.assertEqual(self.presentar(usuario).status_code, 302)

    def test_solo_ve_sus_propias_solicitudes(self):
        propia, ajena = self.solicitud_de(self.e.residente), self.solicitud_de(self.e.residente_b)
        self.client.force_login(self.e.residente)
        self.assertEqual(list(self.client.get(reverse("privacidad:mis_solicitudes")).context["solicitudes"]), [propia])
        self.assertEqual(self.client.get(propia.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(ajena.get_absolute_url()).status_code, 404)

    def test_el_administrador_ve_las_del_condominio_y_no_las_de_otro(self):
        propia, ajena = self.solicitud_de(self.e.residente), self.solicitud_de(self.e.residente_ajeno, self.e.ajeno)
        self.client.force_login(self.e.administrador)
        self.assertEqual(list(self.client.get(reverse("privacidad:solicitudes")).context["solicitudes"]), [propia])
        self.assertEqual(self.client.get(reverse("privacidad:responder", args=[ajena.pk])).status_code, 404)

    def test_solo_el_administrador_ve_y_responde(self):
        solicitud = self.solicitud_de(self.e.residente)
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.email):
                self.assertEqual(self.client.get(reverse("privacidad:solicitudes")).status_code, 403)
                url = reverse("privacidad:responder", args=[solicitud.pk])
                self.assertEqual(self.client.post(url, {"respuesta": "x"}).status_code, 403)
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.esta_pendiente)

    def test_responder_cierra_y_avisa(self):
        solicitud = self.solicitud_de(self.e.residente)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("privacidad:responder", args=[solicitud.pk]), {"respuesta": "Corregido."})
        self.assertRedirects(respuesta, reverse("privacidad:solicitudes"))
        solicitud.refresh_from_db()
        self.assertEqual((solicitud.estado, solicitud.respuesta), (SolicitudTitular.Estado.CERRADA, "Corregido."))
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.residente).exists())

    def test_la_respuesta_es_obligatoria(self):
        solicitud = self.solicitud_de(self.e.residente)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("privacidad:responder", args=[solicitud.pk]), {"respuesta": ""})
        self.assertIn("respuesta", respuesta.context["form"].errors)
        solicitud.refresh_from_db()
        self.assertTrue(solicitud.esta_pendiente)

    def test_una_cerrada_no_se_responde_de_nuevo(self):
        solicitud = self.solicitud_de(self.e.residente)
        solicitud.cerrar("Primera.", por=self.e.administrador)
        self.client.force_login(self.e.administrador)
        self.client.post(reverse("privacidad:responder", args=[solicitud.pk]), {"respuesta": "Segunda."})
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.respuesta, "Primera.")

    def test_la_persona_ve_la_respuesta(self):
        solicitud = self.solicitud_de(self.e.residente)
        solicitud.cerrar("Ya actualizamos tu teléfono.", por=self.e.administrador)
        self.client.force_login(self.e.residente)
        self.assertContains(self.client.get(solicitud.get_absolute_url()), "Ya actualizamos tu teléfono.")

    def test_la_pagina_usuarios_enlaza_las_solicitudes(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("cuentas:usuarios")), reverse("privacidad:solicitudes"))


class DescargarMisDatosTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("privacidad:descargar")

    def descargar(self, usuario=None):
        self.client.force_login(usuario or self.e.residente)
        respuesta = self.client.get(self.url)
        return respuesta, json.loads(respuesta.content)

    def cobro(self, anio, mes):
        periodo = PeriodoGasto.objects.create(
            condominio=self.e.condominio, anio=anio, mes=mes, estado=PeriodoGasto.Estado.EMITIDO
        )
        return DetalleGastoComun.objects.create(periodo=periodo, unidad=self.e.a101, monto=40000, monto_fondo_reserva=2000)

    def test_es_un_archivo_json_descargable(self):
        respuesta, _ = self.descargar()
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertIn('attachment; filename="mis-datos-condohub-', respuesta["Content-Disposition"])
        self.assertIn("no-store", respuesta["Cache-Control"])  # que el navegador no guarde una copia

    def test_incluye_cada_seccion_y_no_la_contrasena(self):
        respuesta, datos = self.descargar()
        self.assertEqual(
            set(datos),
            {"cuenta", "roles", "residencias", "cobros", "reservas", "incidentes", "solicitudes_de_datos", "notificaciones"},
        )
        self.assertEqual(datos["cuenta"]["correo"], "residente@prueba.cl")
        self.assertEqual(datos["residencias"][0]["desde"], "2020-01-01")
        self.assertNotIn(self.e.residente.password, respuesta.content.decode())
        self.assertNotIn("password", respuesta.content.decode())

    def test_solo_trae_los_datos_propios(self):
        _, datos = self.descargar()
        self.assertNotIn("residente.b@prueba.cl", json.dumps(datos))

    def test_los_cobros_respetan_el_periodo_de_residencia(self):
        Residente.objects.filter(usuario=self.e.residente).update(desde=date(2026, 3, 20))
        self.cobro(2026, 2)  # deuda de quien vivió antes
        marzo = self.cobro(2026, 3)
        Pago.registrar(marzo, monto=10000, registrado_por=self.e.administrador)
        _, datos = self.descargar()
        self.assertEqual([c["periodo"] for c in datos["cobros"]], [str(marzo.periodo)])
        self.assertEqual((datos["cobros"][0]["pagado"], datos["cobros"][0]["saldo"]), (10000, 32000))

    def test_quien_fue_dado_de_baja_recibe_los_cobros_de_su_periodo(self):
        marzo = self.cobro(2026, 3)
        Residente.objects.get(usuario=self.e.residente).dar_de_baja()
        _, datos = self.descargar()
        self.assertEqual([c["periodo"] for c in datos["cobros"]], [str(marzo.periodo)])
        self.assertFalse(datos["residencias"][0]["activo"])

    def test_incluye_sus_solicitudes_y_notificaciones(self):
        SolicitudTitular(
            usuario=self.e.residente, condominio=self.e.condominio, tipo=SolicitudTitular.Tipo.ACCESO, detalle="x"
        ).presentar()
        Notificacion.objects.create(usuario=self.e.residente, condominio=self.e.condominio, titulo="Hola", mensaje="m")
        _, datos = self.descargar()
        self.assertEqual(len(datos["solicitudes_de_datos"]), 1)
        self.assertEqual([n["titulo"] for n in datos["notificaciones"]], ["Hola"])

    def test_sin_sesion_pide_iniciarla(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, f"{reverse('cuentas:iniciar_sesion')}?next={self.url}")

    def test_mi_perfil_ofrece_la_descarga(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(reverse("cuentas:perfil"))
        self.assertContains(respuesta, self.url)
        self.assertContains(respuesta, reverse("privacidad:mis_solicitudes"))


class AuditoriaSolicitudesTest(TestCase):
    """Eventos de auditoría de las solicitudes del titular (Refs #27): sin el detalle ni la respuesta."""

    def test_presentar_y_cerrar_quedan_registrados(self):
        e = crear_escenario()
        solicitud = SolicitudTitular(
            usuario=e.residente, condominio=e.condominio, tipo=SolicitudTitular.Tipo.SUPRESION, detalle="Mi teléfono 9876"
        )
        solicitud.presentar()
        solicitud.cerrar("Lo borramos: era el 9876.", por=e.administrador)
        presentar, cerrar = RegistroAuditoria.objects.filter(objeto_tipo="solicitudtitular").order_by("id")
        self.assertEqual((presentar.accion, presentar.usuario_id), ("crear", e.residente.pk))
        self.assertEqual(presentar.despues, {"tipo": "SUPRESION", "estado": "PENDIENTE"})
        self.assertEqual((cerrar.accion, cerrar.usuario_id), ("modificar", e.administrador.pk))
        self.assertEqual((cerrar.antes, cerrar.despues), ({"estado": "PENDIENTE"}, {"estado": "CERRADA"}))
        # Ni el detalle ni la respuesta se copian a la auditoría.
        self.assertNotIn("9876", str(presentar.despues) + str(cerrar.antes) + str(cerrar.despues))
