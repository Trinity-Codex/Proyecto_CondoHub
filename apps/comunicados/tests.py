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
