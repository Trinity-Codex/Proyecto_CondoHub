"""Pruebas de incidentes (RF07, RF08) y sus notificaciones (RF10)."""
from django.test import TestCase
from django.urls import reverse

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
