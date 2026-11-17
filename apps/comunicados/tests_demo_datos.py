"""Comunicados ficticios de la demo del cliente (Issue #96)."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.comunicados.models import Comunicado
from apps.cuentas.models import Usuario


class ComunicadosDemoTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16))
    def test_comunicados_visibles_con_vigencia_y_lectura(self):
        call_command("cargar_demo", stdout=StringIO())
        hoy = timezone.localdate()
        vista_verde = Comunicado.objects.filter(condominio__nombre="Condominio Vista Verde")

        # Vigente general, con fecha de vigencia, publicado (no en el futuro).
        general = vista_verde.get(titulo="Mantención de ascensores esta semana")
        self.assertEqual(general.tipo, Comunicado.Tipo.GENERAL)
        self.assertFalse(general.esta_vencido(hoy))
        self.assertLessEqual(general.fecha_publicacion, timezone.now())

        # Dirigido a la Torre A, vigente, con lectura confirmada por la unidad A-101.
        dirigido = vista_verde.get(titulo="Retiro de bicicletas abandonadas en Torre A")
        self.assertEqual(dirigido.edificio.nombre, "Torre A")
        self.assertFalse(dirigido.esta_vencido(hoy))
        confirmadas, destinatarias = dirigido.confirmaciones()
        self.assertEqual({u.numero for u in confirmadas}, {"101"})
        self.assertGreater(len(destinatarias), len(confirmadas))

        # El vencido solo aparece en «Ver vencidos».
        vencido = vista_verde.get(titulo="Corte de agua programado en Torre B")
        self.assertTrue(vencido.esta_vencido(hoy))

        # El residente de A-101 ve en su lista el general y el dirigido a su torre.
        self.client.force_login(Usuario.objects.get(email="residente@condohub.cl"))
        lista = self.client.get(reverse("comunicados:lista"))
        self.assertContains(lista, general.titulo)
        self.assertContains(lista, dirigido.titulo)

        # El residente de la Torre B no ve el vencido en la lista principal, sí en «Ver vencidos».
        self.client.force_login(Usuario.objects.get(email="residente2@condohub.cl"))
        self.assertNotContains(self.client.get(reverse("comunicados:lista")), vencido.titulo)
        self.assertContains(self.client.get(reverse("comunicados:lista"), {"vigencia": "vencidos"}), vencido.titulo)

    def test_sin_fecha_se_conservan_los_tres(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(Comunicado.objects.count(), 3)
