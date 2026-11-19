"""Pruebas de comunicados (RF09) y su notificación (RF10)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.condominios.models import Residente
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.notificaciones.models import Notificacion

from .models import Comunicado, LecturaComunicado


class ComunicadoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def publicar(self, **campos):
        datos = {"titulo": "Aviso", "contenido": "Texto", "tipo": Comunicado.Tipo.GENERAL, **campos}
        self.client.force_login(self.e.administrador)
        return self.client.post(reverse("comunicados:nuevo"), datos)

    def test_admin_publica_comunicado_general(self):
        respuesta = self.publicar()
        comunicado = Comunicado.objects.get()
        self.assertRedirects(respuesta, comunicado.get_absolute_url())
        self.assertEqual(comunicado.condominio, self.e.condominio)
        self.assertEqual(comunicado.autor, self.e.administrador)

    def test_comunicado_general_notifica_a_residentes_y_comite(self):
        self.publicar()
        avisados = set(Notificacion.objects.values_list("usuario__email", flat=True))
        self.assertEqual(avisados, {"residente@prueba.cl", "residente.b@prueba.cl", "comite@prueba.cl"})

    def test_comunicado_por_edificio_solo_notifica_a_ese_edificio(self):
        self.publicar(tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b.pk)
        avisados = set(Notificacion.objects.values_list("usuario__email", flat=True))
        self.assertEqual(avisados, {"residente.b@prueba.cl", "comite@prueba.cl"})

    def test_por_edificio_exige_edificio(self):
        respuesta = self.publicar(tipo=Comunicado.Tipo.POR_EDIFICIO)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("edificio", respuesta.context["form"].errors)

    def test_residente_no_puede_publicar(self):
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("comunicados:nuevo")).status_code, 403)

    def test_residente_ve_generales_y_de_su_edificio(self):
        general = Comunicado.objects.create(condominio=self.e.condominio, autor=self.e.administrador, titulo="General", contenido="x")
        torre_a = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Torre A", contenido="x",
            tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_a,
        )
        torre_b = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Torre B", contenido="x",
            tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b,
        )
        self.client.force_login(self.e.residente)  # vive en la Torre A
        visibles = list(self.client.get(reverse("comunicados:lista")).context["comunicados"])
        self.assertCountEqual(visibles, [general, torre_a])
        self.assertEqual(self.client.get(torre_b.get_absolute_url()).status_code, 404)

    def test_panel_de_inicio_aplica_la_misma_regla(self):
        # Error encontrado en la revisión visual: el panel mostraba comunicados de otro edificio.
        Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Solo Torre B", contenido="x",
            tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b,
        )
        self.client.force_login(self.e.residente)  # vive en la Torre A
        self.assertEqual(list(self.client.get(reverse("core:inicio")).context["comunicados"]), [])
        self.client.force_login(self.e.residente_b)  # vive en la Torre B
        self.assertEqual(len(self.client.get(reverse("core:inicio")).context["comunicados"]), 1)

    def test_no_se_ven_comunicados_de_otro_condominio(self):
        ajeno = Comunicado.objects.create(condominio=self.e.ajeno, autor=self.e.residente_ajeno, titulo="Ajeno", contenido="x")
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(ajeno.get_absolute_url()).status_code, 404)


# --------------------------------------------------------------------------
# Vigencia y confirmación de lectura (Issue #58, RF13)
# --------------------------------------------------------------------------
class VigenciaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.hoy = timezone.localdate()

    def comunicado(self, titulo, vigente_hasta=None, **campos):
        return Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo=titulo, contenido="x",
            vigente_hasta=vigente_hasta, **campos,
        )

    def test_el_dia_indicado_todavia_es_vigente_y_el_siguiente_no(self):
        hoy_mismo = self.comunicado("Hoy", self.hoy)
        ayer = self.comunicado("Ayer", self.hoy - timedelta(days=1))
        sin_fecha = self.comunicado("Sin fecha")
        self.assertEqual(set(Comunicado.objects.vigentes(self.hoy)), {hoy_mismo, sin_fecha})
        self.assertEqual(list(Comunicado.objects.vencidos(self.hoy)), [ayer])
        self.assertTrue(ayer.esta_vencido(self.hoy))
        self.assertFalse(sin_fecha.esta_vencido(self.hoy))

    def test_el_vencido_sale_de_la_lista_y_del_inicio_pero_se_puede_ver(self):
        vencido = self.comunicado("Asamblea pasada", self.hoy - timedelta(days=1))
        self.comunicado("Corte de luz")
        self.client.force_login(self.e.residente)
        lista = self.client.get(reverse("comunicados:lista"))
        self.assertNotContains(lista, "Asamblea pasada")
        self.assertContains(lista, "Ver vencidos (1)")
        self.assertNotContains(self.client.get(reverse("core:inicio")), "Asamblea pasada")
        vencidos = self.client.get(reverse("comunicados:lista") + "?vigencia=vencidos")
        self.assertContains(vencidos, "Asamblea pasada")
        self.assertNotContains(vencidos, "Corte de luz")
        self.assertContains(vencidos, '<span class="insignia">Vencido</span>', html=True)
        detalle = self.client.get(vencido.get_absolute_url())
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, "Vencido")

    def test_los_vencidos_respetan_la_visibilidad_por_edificio(self):
        self.comunicado("Solo Torre B", self.hoy - timedelta(days=1), tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b)
        self.client.force_login(self.e.residente)  # vive en la Torre A
        self.assertNotContains(self.client.get(reverse("comunicados:lista") + "?vigencia=vencidos"), "Solo Torre B")

    def publicar(self, **campos):
        self.client.force_login(self.e.administrador)
        datos = {"titulo": "Aviso", "contenido": "x", "tipo": Comunicado.Tipo.GENERAL, "vigente_hasta": "", **campos}
        return self.client.post(reverse("comunicados:nuevo"), datos)

    def test_publicar_con_fecha_de_vigencia(self):
        self.publicar(vigente_hasta=(self.hoy + timedelta(days=3)).isoformat())
        self.assertEqual(Comunicado.objects.get(titulo="Aviso").vigente_hasta, self.hoy + timedelta(days=3))

    def test_no_se_publica_con_una_fecha_pasada(self):
        respuesta = self.publicar(vigente_hasta=(self.hoy - timedelta(days=1)).isoformat())
        self.assertContains(respuesta, "La fecha no puede ser anterior a hoy.")
        self.assertFalse(Comunicado.objects.filter(titulo="Aviso").exists())

    def test_editar_un_vencido_sin_cambiar_su_fecha(self):
        ayer = self.hoy - timedelta(days=1)
        vencido = self.comunicado("Asamblea", ayer)
        self.client.force_login(self.e.administrador)
        self.client.post(
            reverse("comunicados:editar", args=[vencido.pk]),
            {"titulo": "Asamblea (acta)", "contenido": "x", "tipo": Comunicado.Tipo.GENERAL, "vigente_hasta": ayer.isoformat()},
        )
        vencido.refresh_from_db()
        self.assertEqual((vencido.titulo, vencido.vigente_hasta), ("Asamblea (acta)", ayer))


class LecturaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.general = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Asamblea", contenido="x"
        )

    def marcar(self, usuario, comunicado=None):
        self.client.force_login(usuario)
        return self.client.post(reverse("comunicados:marcar_leido", args=[(comunicado or self.general).pk]))

    def test_el_residente_marca_una_sola_vez(self):
        respuesta = self.marcar(self.e.residente)
        self.assertRedirects(respuesta, self.general.get_absolute_url())
        self.marcar(self.e.residente)
        self.assertEqual(LecturaComunicado.objects.filter(usuario=self.e.residente).count(), 1)
        detalle = self.client.get(self.general.get_absolute_url())
        self.assertContains(detalle, "Leíste este comunicado")
        self.assertNotContains(detalle, "Marcar como leído")

    def test_conteo_por_unidad_y_solo_de_unidades_con_residentes(self):
        # Destinatarias: A101 y B101 (A102 no tiene residentes). Dos residentes de A101 leen.
        companera = crear_usuario("companera@prueba.cl")
        Residente.objects.create(usuario=companera, unidad=self.e.a101, tipo=Residente.Tipo.FAMILIAR)
        self.marcar(self.e.residente)
        self.marcar(companera)
        confirmadas, destinatarias = self.general.confirmaciones()
        self.assertEqual(destinatarias, {self.e.a101, self.e.b101})
        self.assertEqual(confirmadas, {self.e.a101})

    def test_por_edificio_cuenta_solo_las_unidades_de_ese_edificio(self):
        solo_b = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Torre B", contenido="x",
            tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b,
        )
        self.marcar(self.e.residente_b, solo_b)
        self.assertEqual(solo_b.confirmaciones(), ({self.e.b101}, {self.e.b101}))

    def test_quien_se_mudo_deja_de_contar(self):
        self.marcar(self.e.residente)
        Residente.objects.get(usuario=self.e.residente).dar_de_baja()
        confirmadas, destinatarias = self.general.confirmaciones()
        self.assertEqual((confirmadas, destinatarias), (set(), {self.e.b101}))

    def test_el_administrador_ve_el_conteo_y_las_unidades_que_faltan(self):
        self.marcar(self.e.residente)
        self.client.force_login(self.e.administrador)
        detalle = self.client.get(self.general.get_absolute_url())
        self.assertContains(detalle, "Unidades que confirmaron la lectura: <strong class=\"text-nowrap\">1 de 2</strong>", html=True)
        self.assertEqual(detalle.context["faltan"], [self.e.b101])
        self.assertContains(self.client.get(reverse("comunicados:lista")), "Unidades que confirmaron la lectura: 1 de 2")

    def test_solo_el_administrador_ve_el_conteo(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertNotContains(self.client.get(self.general.get_absolute_url()), "Unidades que confirmaron")
                self.assertNotContains(self.client.get(reverse("comunicados:lista")), "Unidades que confirmaron")

    def test_acceso_por_rol(self):
        solo_b = Comunicado.objects.create(
            condominio=self.e.condominio, autor=self.e.administrador, titulo="Torre B", contenido="x",
            tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b,
        )
        self.assertEqual(self.marcar(self.e.residente, solo_b).status_code, 404)  # vive en la Torre A
        self.assertEqual(self.marcar(self.e.residente_ajeno).status_code, 404)  # otro condominio
        for usuario in (self.e.comite, self.e.conserje):
            with self.subTest(usuario=usuario):
                self.assertEqual(self.marcar(usuario).status_code, 403)
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("comunicados:marcar_leido", args=[self.general.pk])).status_code, 405)
        self.assertFalse(LecturaComunicado.objects.exists())


# ---------------------------------------------------------------------------
# Aviso prioritario (#118, RQ-03)
# ---------------------------------------------------------------------------
from unittest import mock  # noqa: E402

from apps.condominios.models import Membresia  # noqa: E402
from apps.core.middleware_demo import es_escritura_bloqueada  # noqa: E402


class AvisoPrioritarioTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.hoy = timezone.localdate()
        self.url_aviso = reverse("comunicados:aviso_prioritario")

    def aviso(self, titulo="Simulacro", condominio=None, **campos):
        datos = {"prioritario": True, "vigente_hasta": self.hoy + timedelta(days=3), **campos}
        aviso = Comunicado(condominio=condominio or self.e.condominio, autor=self.e.administrador,
                           titulo=titulo, contenido="Detalle del aviso", **datos)
        aviso.publicar()
        return aviso

    def confirmar(self, aviso):
        return self.client.post(reverse("comunicados:confirmar_aviso", args=[aviso.pk]))

    def assertBloqueado(self, ruta):
        self.assertRedirects(self.client.get(ruta), self.url_aviso, fetch_redirect_response=False)

    # Bloqueo -------------------------------------------------------------------
    def test_bloquea_cualquier_pagina_hasta_confirmar(self):
        aviso = self.aviso()
        self.client.force_login(self.e.residente)
        for ruta in (reverse("core:inicio"), reverse("reservas:espacios"), reverse("comunicados:lista"),
                     reverse("cuentas:perfil"), "/reservas/espacios/999/"):
            with self.subTest(ruta=ruta):
                self.assertBloqueado(ruta)
        pantalla = self.client.get(self.url_aviso)
        self.assertContains(pantalla, "Simulacro")
        self.assertContains(pantalla, 'role="alertdialog"')
        self.assertContains(pantalla, "He leído este aviso")
        # Un POST a otra ruta tampoco pasa.
        self.assertRedirects(self.client.post(reverse("reservas:nueva")), self.url_aviso, fetch_redirect_response=False)

        antes = timezone.now()
        self.confirmar(aviso)
        lectura = LecturaComunicado.objects.get(comunicado=aviso, usuario=self.e.residente)
        self.assertGreaterEqual(lectura.leido, antes)
        self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)
        self.assertEqual(self.client.get(reverse("comunicados:lista")).status_code, 200)

    def test_al_confirmar_vuelve_a_la_pagina_pedida(self):
        aviso = self.aviso()
        self.client.force_login(self.e.residente)
        self.client.get(reverse("reservas:espacios") + "?x=1")
        self.assertRedirects(self.confirmar(aviso), self.url_aviso, fetch_redirect_response=False)
        self.assertRedirects(self.client.get(self.url_aviso), reverse("reservas:espacios") + "?x=1",
                             fetch_redirect_response=False)

    def test_no_sigue_un_destino_externo(self):
        aviso = self.aviso()
        self.client.force_login(self.e.residente)
        self.confirmar(aviso)
        sesion = self.client.session
        sesion["aviso_prioritario_siguiente"] = "https://otro-sitio.example/robar"
        sesion.save()
        self.assertRedirects(self.client.get(self.url_aviso), reverse("core:inicio"), fetch_redirect_response=False)

    def test_varios_avisos_de_a_uno_por_orden_de_publicacion(self):
        primero, segundo = self.aviso("Primero"), self.aviso("Segundo")
        self.client.force_login(self.e.residente)
        pantalla = self.client.get(self.url_aviso)
        self.assertContains(pantalla, "Primero")
        self.assertNotContains(pantalla, "Segundo")
        self.assertContains(pantalla, "1 de 2")
        self.confirmar(primero)
        self.assertContains(self.client.get(self.url_aviso), "Segundo")
        self.confirmar(segundo)
        self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)

    def test_vencido_o_normal_no_bloquea(self):
        self.aviso("Vencido", vigente_hasta=self.hoy - timedelta(days=1))
        Comunicado(condominio=self.e.condominio, autor=self.e.administrador, titulo="Normal",
                   contenido="x", vigente_hasta=self.hoy + timedelta(days=3)).publicar()
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)
        self.assertRedirects(self.client.get(self.url_aviso), reverse("core:inicio"), fetch_redirect_response=False)

    def test_solo_bloquea_al_rol_residente(self):
        self.aviso()
        # El comité de prueba también vive en el condominio: tiene un rol de administración, no se bloquea.
        Residente.objects.create(usuario=self.e.comite, unidad=self.e.a102, desde=self.hoy)
        for persona in (self.e.administrador, self.e.comite, self.e.conserje):
            with self.subTest(persona=persona.email):
                self.client.force_login(persona)
                self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)
                # Sin rol de residente, 403; el comité que además vive ahí vuelve al inicio sin ver el aviso.
                self.assertIn(self.client.get(self.url_aviso).status_code, (302, 403))

    def test_aviso_de_un_edificio_solo_bloquea_a_sus_residentes(self):
        self.aviso(tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b)
        self.client.force_login(self.e.residente)  # Torre A
        self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)
        self.client.force_login(self.e.residente_b)  # Torre B
        self.assertBloqueado(reverse("core:inicio"))

    def test_cerrar_sesion_funciona_siempre(self):
        self.aviso()
        self.client.force_login(self.e.residente)
        self.client.post(reverse("cuentas:cerrar_sesion"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_aislamiento_entre_condominios(self):
        aviso = self.aviso()
        self.client.force_login(self.e.residente_ajeno)
        self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)
        self.assertEqual(self.confirmar(aviso).status_code, 404)
        self.assertFalse(LecturaComunicado.objects.filter(usuario=self.e.residente_ajeno).exists())
        # Un comunicado normal no se confirma por la ruta del aviso.
        normal = Comunicado(condominio=self.e.condominio, autor=self.e.administrador, titulo="N", contenido="x")
        normal.publicar()
        self.client.force_login(self.e.residente)
        self.assertEqual(self.confirmar(normal).status_code, 404)

    def test_falla_abierta(self):
        self.aviso()
        self.client.force_login(self.e.residente)
        with mock.patch("apps.comunicados.middleware.aviso_pendiente", side_effect=RuntimeError("caída")), \
                self.assertLogs("apps.comunicados.middleware", "ERROR"):
            self.assertEqual(self.client.get(reverse("core:inicio")).status_code, 200)

    # Lectura por residente ------------------------------------------------------
    def test_administrador_y_comite_ven_quien_leyo_con_fecha_y_hora(self):
        aviso = self.aviso()
        self.client.force_login(self.e.residente)
        self.confirmar(aviso)
        url = reverse("comunicados:lecturas", args=[aviso.pk])
        for persona in (self.e.administrador, self.e.comite):
            with self.subTest(persona=persona.email):
                self.client.force_login(persona)
                respuesta = self.client.get(url)
                self.assertContains(respuesta, "Confirmaron <strong>1 de 2</strong>", html=False)
                filas = dict((u.email, (unidades, leido)) for u, unidades, leido in respuesta.context["confirmaron"])
                self.assertIn(self.e.residente.email, filas)
                self.assertEqual([u.email for u, *_ in respuesta.context["faltan"]], [self.e.residente_b.email])
                self.assertContains(respuesta, timezone.localtime(filas[self.e.residente.email][1]).strftime("%d-%m-%Y %H:%M"))

    def test_el_residente_nunca_ve_la_lectura_de_otros(self):
        aviso = self.aviso()
        url = reverse("comunicados:lecturas", args=[aviso.pk])
        for persona in (self.e.residente, self.e.conserje):
            with self.subTest(persona=persona.email):
                self.client.force_login(persona)
                if persona == self.e.residente:
                    self.confirmar(aviso)
                self.assertEqual(self.client.get(url).status_code, 403)
        # Desde otro condominio, 404.
        ajeno = Membresia.objects.create(usuario=crear_usuario("admin.ajeno@prueba.cl"), condominio=self.e.ajeno,
                                         rol=Membresia.Rol.ADMINISTRADOR).usuario
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 404)

    # Formulario y demo ----------------------------------------------------------
    def test_prioritario_exige_visible_hasta(self):
        self.client.force_login(self.e.administrador)
        datos = {"titulo": "Urgente", "contenido": "x", "tipo": Comunicado.Tipo.GENERAL, "prioritario": "on"}
        respuesta = self.client.post(reverse("comunicados:nuevo"), datos)
        self.assertContains(respuesta, "Un aviso prioritario necesita la fecha")
        self.assertFalse(Comunicado.objects.exists())
        datos["vigente_hasta"] = (self.hoy + timedelta(days=2)).isoformat()
        self.client.post(reverse("comunicados:nuevo"), datos)
        self.assertTrue(Comunicado.objects.get().prioritario)

    def test_la_demo_de_solo_lectura_permite_confirmar(self):
        self.assertFalse(es_escritura_bloqueada("POST", "comunicados:confirmar_aviso"))
        self.assertTrue(es_escritura_bloqueada("POST", "comunicados:marcar_leido"))


# ---------------------------------------------------------------------------
# Seguimiento de lectura (#120, RQ-04)
# ---------------------------------------------------------------------------
from io import StringIO  # noqa: E402

from django.core import mail  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import override_settings  # noqa: E402

from apps.core.pruebas import CLAVE  # noqa: E402

from .models import AjustesComunicados, RecordatorioComunicado  # noqa: E402
from .recordatorios import enviar_recordatorios_comunicados  # noqa: E402


@override_settings(SITIO_URL="https://condohub.example")
class SeguimientoLecturaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.hoy = timezone.localdate()

    def comunicado(self, titulo="Corte de agua", hace_dias=0, **campos):
        c = Comunicado(condominio=self.e.condominio, autor=self.e.administrador, titulo=titulo,
                       contenido="Detalle", **campos)
        with self.captureOnCommitCallbacks(execute=True):
            c.publicar()
        if hace_dias:
            Comunicado.objects.filter(pk=c.pk).update(fecha_publicacion=timezone.now() - timedelta(days=hace_dias))
            c.refresh_from_db()
        return c

    def leer(self, comunicado, usuario):
        LecturaComunicado.objects.create(comunicado=comunicado, usuario=usuario)

    # Contador -------------------------------------------------------------------
    def test_contador_de_no_leidos_del_residente(self):
        uno, dos = self.comunicado("Uno"), self.comunicado("Dos")
        self.comunicado("De la Torre B", tipo=Comunicado.Tipo.POR_EDIFICIO, edificio=self.e.torre_b)
        self.comunicado("Vencido", vigente_hasta=self.hoy - timedelta(days=1))
        Comunicado(condominio=self.e.ajeno, autor=self.e.administrador, titulo="Ajeno", contenido="x").publicar()
        self.client.force_login(self.e.residente)  # Torre A
        self.assertEqual(self.client.get(reverse("core:inicio")).context["comunicados_sin_leer"], 2)
        self.assertContains(self.client.get(reverse("core:inicio")), "2<span class=\"visually-hidden\"> sin leer</span>",
                            html=False)
        self.client.post(reverse("comunicados:marcar_leido", args=[uno.pk]))
        self.assertEqual(self.client.get(reverse("core:inicio")).context["comunicados_sin_leer"], 1)
        self.leer(dos, self.e.residente)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertEqual(respuesta.context["comunicados_sin_leer"], 0)
        self.assertNotContains(respuesta, "sin leer</span>")

    def test_el_contador_es_solo_para_residentes(self):
        self.comunicado()
        for persona in (self.e.administrador, self.e.comite, self.e.conserje):
            with self.subTest(persona=persona.email):
                self.client.force_login(persona)
                self.assertEqual(self.client.get(reverse("core:inicio")).context["comunicados_sin_leer"], 0)

    # Correo -------------------------------------------------------------------------
    def test_correo_con_asunto_claro_y_enlace_directo(self):
        c = self.comunicado("Corte de agua el sábado")
        correos = {m.to[0]: m for m in mail.outbox}
        self.assertIn(self.e.residente.email, correos)
        correo = correos[self.e.residente.email]
        self.assertEqual(correo.subject, "[CondoHub] Nuevo comunicado: Corte de agua el sábado")
        self.assertIn(f"https://condohub.example{c.get_absolute_url()}", correo.body)
        self.assertNotIn(self.e.residente_b.email, correo.body)  # sin datos de otros residentes
        mail.outbox.clear()
        self.comunicado("Simulacro", prioritario=True, vigente_hasta=self.hoy + timedelta(days=2))
        self.assertTrue(all(m.subject == "[CondoHub] Aviso importante: Simulacro" for m in mail.outbox))

    def test_un_salto_de_linea_no_rompe_el_asunto(self):
        self.comunicado("Línea uno\nlínea dos")
        self.assertTrue(mail.outbox)
        self.assertTrue(all("\n" not in m.subject for m in mail.outbox))

    def test_el_enlace_lleva_al_comunicado_tras_iniciar_sesion(self):
        c = self.comunicado()
        respuesta = self.client.get(c.get_absolute_url())
        self.assertEqual(respuesta.status_code, 302)
        login = respuesta["Location"]
        self.assertIn("next=", login)
        destino = self.client.post(login, {"username": self.e.residente.email, "password": CLAVE})
        self.assertRedirects(destino, c.get_absolute_url())

    # Porcentajes ------------------------------------------------------------------
    def test_porcentaje_de_lectura_por_residente_y_por_unidad(self):
        c = self.comunicado()  # residente (A101) y residente_b (B101): dos personas, dos unidades
        self.assertEqual(c.porcentajes_de_lectura(), (0, 0))
        self.leer(c, self.e.residente)
        self.assertEqual(c.porcentajes_de_lectura(), (50, 50))
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("comunicados:lecturas", args=[c.pk])), "(50 %)")
        self.assertContains(self.client.get(reverse("comunicados:lista")), "Lectura por residente: <strong>50 %</strong>",
                            html=False)
        sin_destinatarios = Comunicado(condominio=self.e.ajeno, autor=self.e.administrador, titulo="x", contenido="x")
        sin_destinatarios.save()
        Residente.objects.filter(unidad__edificio__condominio=self.e.ajeno).update(activo=False)
        self.assertEqual(sin_destinatarios.porcentajes_de_lectura(), (None, None))

    # Recordatorio --------------------------------------------------------------------
    def test_recordatorio_una_vez_y_solo_a_quien_no_leyo(self):
        c = self.comunicado(hace_dias=3)
        self.leer(c, self.e.residente)
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(enviar_recordatorios_comunicados(self.hoy), 1)
        self.assertEqual(list(RecordatorioComunicado.objects.values_list("usuario__email", flat=True)),
                         [self.e.residente_b.email])
        self.assertEqual([m.to for m in mail.outbox], [[self.e.residente_b.email]])
        self.assertEqual(mail.outbox[0].subject, "[CondoHub] Recordatorio: Corte de agua")
        self.assertTrue(Notificacion.objects.filter(usuario=self.e.residente_b, titulo="Tienes un comunicado sin leer").exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.e.comite, titulo="Tienes un comunicado sin leer").exists())
        # Correrlo otra vez, u otro día dentro de la ventana, no repite.
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy), 0)
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy + timedelta(days=2)), 0)

    def test_respeta_el_plazo_de_cada_condominio(self):
        self.comunicado(hace_dias=3)
        AjustesComunicados.objects.create(condominio=self.e.condominio, dias_recordatorio=5)
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy), 0)
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy + timedelta(days=2)), 2)

    def test_no_recuerda_antes_del_plazo_viejos_vencidos_ni_cuentas_inactivas(self):
        self.comunicado("Reciente", hace_dias=2)
        self.comunicado("Viejo", hace_dias=20)
        self.comunicado("Vencido", hace_dias=4, vigente_hasta=self.hoy - timedelta(days=1))
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy), 0)
        c = self.comunicado("Normal", hace_dias=3)
        self.e.residente_b.is_active = False
        self.e.residente_b.save()
        self.assertEqual(enviar_recordatorios_comunicados(self.hoy), 1)
        self.assertEqual(RecordatorioComunicado.objects.get().comunicado, c)

    def test_comando(self):
        self.comunicado(hace_dias=3)
        salida = StringIO()
        call_command("enviar_recordatorios_comunicados", "--fecha", self.hoy.isoformat(), stdout=salida)
        self.assertIn(": 2.", salida.getvalue())
        with self.assertRaisesMessage(Exception, "AAAA-MM-DD"):
            call_command("enviar_recordatorios_comunicados", "--fecha", "25/11/2026", stdout=StringIO())

    # Ajustes ---------------------------------------------------------------------------
    def test_solo_el_administrador_ajusta_el_plazo(self):
        url = reverse("comunicados:ajustes")
        self.assertEqual(AjustesComunicados.dias_de(self.e.condominio), 3)
        for persona in (self.e.comite, self.e.conserje, self.e.residente):
            with self.subTest(persona=persona.email):
                self.client.force_login(persona)
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(AjustesComunicados.objects.exists())  # abrir la página no crea la fila
        for malo in ("0", "31"):
            self.assertEqual(self.client.post(url, {"dias_recordatorio": malo}).status_code, 200)
        self.client.post(url, {"dias_recordatorio": "7"})
        self.assertEqual(AjustesComunicados.dias_de(self.e.condominio), 7)
        self.assertEqual(AjustesComunicados.dias_de(self.e.ajeno), 3)
