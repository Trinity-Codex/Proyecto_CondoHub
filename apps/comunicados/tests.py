"""Pruebas de comunicados (RF09) y su notificación (RF10)."""
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario
from apps.notificaciones.models import Notificacion

from .models import Comunicado


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
