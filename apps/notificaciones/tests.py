"""Pruebas del patrón Observer y de las notificaciones (RF10)."""
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario

from .models import Notificacion
from .observador import Evento, Observador, Sujeto


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
