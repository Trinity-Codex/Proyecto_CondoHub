"""Pruebas de incidentes (RF07, RF08) y sus notificaciones (RF10)."""
from datetime import timedelta
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import RegistroAuditoria
from apps.core.pruebas import crear_escenario
from apps.notificaciones.models import Notificacion

from .models import Incidente


class IncidenteTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def reportar(self, usuario=None):
        self.client.force_login(usuario or self.e.residente)
        self.client.post(reverse("incidentes:nuevo"), {
            "categoria": Incidente.Categoria.MANTENCION, "titulo": "Fuga de agua",
            "unidad": self.e.a101.pk, "descripcion": "Gotea el techo del baño.",
        })
        return Incidente.objects.latest("pk")

    def test_residente_reporta_y_avisa_a_admin_y_conserje(self):
        incidente = self.reportar()
        self.assertEqual(incidente.reportado_por, self.e.residente)
        self.assertEqual(incidente.estado, Incidente.Estado.RECIBIDO)
        avisados = set(Notificacion.objects.values_list("usuario__email", flat=True))
        self.assertEqual(avisados, {"admin@prueba.cl", "conserje@prueba.cl"})

    def test_conserje_cambia_estado_y_avisa_al_residente(self):
        incidente = self.reportar()
        Notificacion.objects.all().delete()
        self.client.force_login(self.e.conserje)
        self.client.post(incidente.get_absolute_url(), {"estado": Incidente.Estado.EN_PROCESO, "respuesta": "Vamos en camino"})
        incidente.refresh_from_db()
        self.assertEqual(incidente.estado, Incidente.Estado.EN_PROCESO)
        self.assertEqual(incidente.respuesta, "Vamos en camino")
        self.assertEqual(Notificacion.objects.get().usuario, self.e.residente)

    def test_residente_no_puede_cambiar_estado(self):
        incidente = self.reportar()
        self.client.post(incidente.get_absolute_url(), {"estado": Incidente.Estado.RESUELTO})
        incidente.refresh_from_db()
        self.assertEqual(incidente.estado, Incidente.Estado.RECIBIDO)

    def test_residente_solo_ve_sus_incidentes(self):
        propio = self.reportar()
        ajeno = Incidente.objects.create(
            condominio=self.e.condominio, reportado_por=self.e.residente_b,
            categoria=Incidente.Categoria.RUIDOS, titulo="Ruidos", descripcion="x",
        )
        self.client.force_login(self.e.residente)
        visibles = list(self.client.get(reverse("incidentes:lista")).context["incidentes"])
        self.assertEqual(visibles, [propio])
        self.assertEqual(self.client.get(ajeno.get_absolute_url()).status_code, 404)

    def test_filtro_por_estado(self):
        self.reportar()
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("incidentes:lista"), {"estado": Incidente.Estado.RESUELTO})
        self.assertEqual(len(respuesta.context["incidentes"]), 0)


class FiltroYOrdenTest(TestCase):
    """Chips, filtro por ?estado= y orden por urgencia de la lista (Issue #80)."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("incidentes:lista")
        # Antiguos primero: resuelto viejo, recibido, en proceso, resuelto reciente, recibido reciente.
        self.resuelto_viejo = self.crear(Incidente.Estado.RESUELTO, dias=40)
        self.recibido_viejo = self.crear(Incidente.Estado.RECIBIDO, dias=30)
        self.en_proceso = self.crear(Incidente.Estado.EN_PROCESO, dias=20)
        self.resuelto_reciente = self.crear(Incidente.Estado.RESUELTO, dias=2)
        self.recibido_reciente = self.crear(Incidente.Estado.RECIBIDO, dias=1)
        self.client.force_login(self.e.administrador)

    def crear(self, estado, dias=0, condominio=None, usuario=None):
        incidente = Incidente.objects.create(
            condominio=condominio or self.e.condominio, reportado_por=usuario or self.e.residente,
            categoria=Incidente.Categoria.OTRO, titulo=f"{estado} {dias}", descripcion="x", estado=estado,
        )
        # fecha_reporte es auto_now_add: se corrige con update para fijar la antigüedad.
        Incidente.objects.filter(pk=incidente.pk).update(fecha_reporte=timezone.now() - timedelta(days=dias))
        return incidente

    def cantidades(self, respuesta):
        return {c["valor"]: c["cantidad"] for c in respuesta.context["chips"]}

    def test_filtro_valido_filtra_y_los_chips_cuentan_todos_los_estados(self):
        respuesta = self.client.get(self.url, {"estado": "EN_PROCESO"})
        self.assertEqual([i.pk for i in respuesta.context["incidentes"]], [self.en_proceso.pk])
        self.assertEqual(self.cantidades(respuesta), {"": 5, "RECIBIDO": 2, "EN_PROCESO": 1, "RESUELTO": 2})
        activos = [c["valor"] for c in respuesta.context["chips"] if c["activo"]]
        self.assertEqual(activos, ["EN_PROCESO"])

    def test_filtro_desconocido_se_ignora(self):
        respuesta = self.client.get(self.url, {"estado": "XYZ"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["incidentes"]), 5)
        self.assertFalse(respuesta.context["hay_filtros"])
        self.assertNotContains(respuesta, "Limpiar filtros")
        self.assertEqual([c["valor"] for c in respuesta.context["chips"] if c["activo"]], [""])

    def test_el_chip_activo_lleva_aria_current_y_la_cantidad_se_lee_completa(self):
        respuesta = self.client.get(self.url, {"estado": "RECIBIDO"})
        self.assertContains(respuesta, 'aria-current="true"', count=1)
        self.assertContains(respuesta, '<span class="visually-hidden">, 2 incidentes</span>', html=True)
        self.assertContains(respuesta, '<span class="visually-hidden">, 1 incidente</span>', html=True)
        self.assertContains(respuesta, "Limpiar filtros")

    def test_orden_por_urgencia(self):
        respuesta = self.client.get(self.url)
        orden = [i.pk for i in respuesta.context["incidentes"]]
        self.assertEqual(orden, [
            self.recibido_viejo.pk, self.recibido_reciente.pk, self.en_proceso.pk,
            self.resuelto_reciente.pk, self.resuelto_viejo.pk,
        ])

    def test_un_recibido_antiguo_va_antes_que_un_resuelto_reciente(self):
        orden = [i.pk for i in self.client.get(self.url).context["incidentes"]]
        self.assertLess(orden.index(self.recibido_viejo.pk), orden.index(self.resuelto_reciente.pk))

    def test_aislamiento_otro_condominio_no_suma_ni_aparece(self):
        ajeno = self.crear(Incidente.Estado.RECIBIDO, condominio=self.e.ajeno, usuario=self.e.residente_ajeno)
        respuesta = self.client.get(self.url)
        self.assertEqual(self.cantidades(respuesta)[""], 5)
        self.assertEqual(self.cantidades(respuesta)["RECIBIDO"], 2)
        self.assertNotIn(ajeno.pk, [i.pk for i in respuesta.context["incidentes"]])

    def test_el_residente_cuenta_solo_sus_incidentes(self):
        ajeno = self.crear(Incidente.Estado.RECIBIDO, usuario=self.e.residente_b)
        self.client.force_login(self.e.residente_b)
        respuesta = self.client.get(self.url)
        self.assertEqual(self.cantidades(respuesta), {"": 1, "RECIBIDO": 1, "EN_PROCESO": 0, "RESUELTO": 0})
        self.assertEqual([i.pk for i in respuesta.context["incidentes"]], [ajeno.pk])

    def test_chips_limpiar_y_paginacion_conservan_el_resto_de_la_url(self):
        for _ in range(16):
            self.crear(Incidente.Estado.RECIBIDO)
        respuesta = self.client.get(self.url, {"estado": "RECIBIDO", "otro": "1", "page": "1"})
        self.assertContains(respuesta, 'href="?estado=RECIBIDO&amp;otro=1&page=2"')
        self.assertContains(respuesta, 'href="?estado=EN_PROCESO&amp;otro=1"')  # el chip quita page
        self.assertContains(respuesta, 'href="?otro=1"')  # «Todos» y «Limpiar filtros»

    def test_una_sola_consulta_cuenta_los_estados(self):
        self.client.get(self.url)  # calienta cachés (sesión, tipos de contenido) para comparar justo
        with CaptureQueriesContext(connection) as consultas:
            self.client.get(self.url, {"estado": "RECIBIDO"})
        agrupadas = [q["sql"] for q in consultas if "GROUP BY" in q["sql"]]
        self.assertEqual(len(agrupadas), 1)
        # Con más estados o filtros no crece: mismas consultas con y sin filtro.
        with CaptureQueriesContext(connection) as sin_filtro:
            self.client.get(self.url)
        self.assertEqual(len(consultas), len(sin_filtro))

    def test_la_insignia_usa_la_paleta_propia(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, '<span class="insignia insignia-recibido">Recibido</span>', html=True)
        self.assertContains(respuesta, '<span class="insignia insignia-resuelto">Resuelto</span>', html=True)
        self.assertNotContains(respuesta, "badge text-bg")


class AuditoriaCambioDeEstadoTest(TestCase):
    """#27 (6.2): el cambio de estado desde la vista queda en la auditoría, en la misma transacción."""

    def setUp(self):
        self.e = crear_escenario()
        self.incidente = Incidente.objects.create(
            condominio=self.e.condominio, reportado_por=self.e.residente,
            categoria=Incidente.Categoria.ASEO, titulo="Basura", descripcion="Piso 2",
        )

    def cambiar(self, usuario, estado, respuesta=""):
        self.client.force_login(usuario)
        return self.client.post(self.incidente.get_absolute_url(), {"estado": estado, "respuesta": respuesta})

    def test_administrador_y_conserje_dejan_modificar_con_estados_reales(self):
        self.cambiar(self.e.administrador, Incidente.Estado.EN_PROCESO)
        self.cambiar(self.e.conserje, Incidente.Estado.RESUELTO)
        primero, segundo = RegistroAuditoria.objects.order_by("pk")
        for registro, actor in ((primero, self.e.administrador), (segundo, self.e.conserje)):
            self.assertEqual(registro.accion, "modificar")
            self.assertEqual(registro.objeto_tipo, "incidente")
            self.assertEqual(registro.objeto_id, str(self.incidente.pk))
            self.assertEqual(registro.condominio_id, self.e.condominio.pk)
            self.assertEqual(registro.usuario_id, actor.pk)
        self.assertEqual((primero.antes, primero.despues), ({"estado": "RECIBIDO"}, {"estado": "EN_PROCESO"}))
        self.assertEqual((segundo.antes, segundo.despues), ({"estado": "EN_PROCESO"}, {"estado": "RESUELTO"}))

    def test_estado_igual_no_audita_pero_conserva_respuesta_y_aviso(self):
        respuesta = self.cambiar(self.e.administrador, Incidente.Estado.RECIBIDO, "Lo revisamos")
        self.assertRedirects(respuesta, self.incidente.get_absolute_url())
        self.incidente.refresh_from_db()
        self.assertEqual(self.incidente.respuesta, "Lo revisamos")
        self.assertEqual(RegistroAuditoria.objects.count(), 0)
        self.assertEqual(Notificacion.objects.filter(usuario=self.e.residente).count(), 1)

    def test_residente_no_audita(self):
        self.cambiar(self.e.residente, Incidente.Estado.RESUELTO)
        self.assertEqual(RegistroAuditoria.objects.count(), 0)

    def test_usa_el_estado_persistido_y_no_el_de_una_instancia_desactualizada(self):
        obsoleta = Incidente.objects.get(pk=self.incidente.pk)
        Incidente.objects.filter(pk=obsoleta.pk).update(estado=Incidente.Estado.EN_PROCESO)
        obsoleta.cambiar_estado(Incidente.Estado.RESUELTO, usuario=self.e.administrador)
        registro = RegistroAuditoria.objects.get()
        self.assertEqual((registro.antes, registro.despues), ({"estado": "EN_PROCESO"}, {"estado": "RESUELTO"}))
        # Con el mismo estado que ya tiene la base, aunque la instancia diga otra cosa, no hay evento.
        obsoleta.estado = Incidente.Estado.RECIBIDO
        obsoleta.cambiar_estado(Incidente.Estado.RESUELTO, usuario=self.e.administrador)
        self.assertEqual(RegistroAuditoria.objects.count(), 1)

    def test_sin_usuario_audita_como_sistema(self):
        self.incidente.cambiar_estado(Incidente.Estado.EN_PROCESO)
        registro = RegistroAuditoria.objects.get()
        self.assertIsNone(registro.usuario_id)
        self.assertEqual(registro.usuario_nombre, "Sistema")
        self.assertEqual((registro.antes, registro.despues), ({"estado": "RECIBIDO"}, {"estado": "EN_PROCESO"}))

    def test_si_falla_la_auditoria_se_revierte_el_cambio_y_el_aviso(self):
        with mock.patch("apps.incidentes.models.registrar", side_effect=RuntimeError("falla controlada")):
            with self.assertRaises(RuntimeError):
                self.cambiar(self.e.administrador, Incidente.Estado.RESUELTO, "Listo")
        self.incidente.refresh_from_db()
        self.assertEqual(self.incidente.estado, Incidente.Estado.RECIBIDO)
        self.assertEqual(self.incidente.respuesta, "")
        self.assertEqual(Notificacion.objects.count(), 0)

    def test_si_falla_el_aviso_se_revierte_tambien_la_auditoria(self):
        with mock.patch.object(Incidente, "notificar", side_effect=RuntimeError("falla controlada")):
            with self.assertRaises(RuntimeError):
                self.cambiar(self.e.administrador, Incidente.Estado.RESUELTO)
        self.incidente.refresh_from_db()
        self.assertEqual(self.incidente.estado, Incidente.Estado.RECIBIDO)
        self.assertEqual(RegistroAuditoria.objects.count(), 0)
