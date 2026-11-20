"""Incidentes ficticios de la demo del cliente (Issue #98)."""
import os
import tempfile
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.incidentes.models import FotoIncidente, Incidente


class IncidentesDemoTest(TestCase):
    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16))
    def test_tres_estados_incidente_solo_modo_cliente(self):
        call_command("cargar_demo", stdout=StringIO())
        estados = sorted(Incidente.objects.values_list("estado", flat=True))
        self.assertEqual(estados, ["EN_PROCESO", "RECIBIDO", "RESUELTO"])
        resuelto = Incidente.objects.get(estado=Incidente.Estado.RESUELTO)
        self.assertEqual(resuelto.condominio.nombre, "Condominio Vista Verde")
        self.assertTrue(resuelto.respuesta)  # el residente ve cómo se resolvió

    def test_sin_fecha_no_hay_resuelto(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertFalse(Incidente.objects.filter(estado=Incidente.Estado.RESUELTO).exists())
        self.assertEqual(Incidente.objects.count(), 2)

    def test_resuelto_trae_fotos_antes_y_despues_ficticias(self):
        # Se usa una carpeta temporal que se borra sola.
        with tempfile.TemporaryDirectory() as carpeta, override_settings(
            DEMO_FECHA_REFERENCIA=date(2026, 11, 16), MEDIA_ROOT=carpeta
        ):
            call_command("cargar_demo", stdout=StringIO())
            resuelto = Incidente.objects.get(estado=Incidente.Estado.RESUELTO)
            fotos = {f.etapa: f for f in resuelto.fotos.select_related("subido_por")}
            self.assertEqual(set(fotos), {FotoIncidente.Etapa.ANTES, FotoIncidente.Etapa.DESPUES})
            self.assertEqual(fotos["ANTES"].subido_por.email, "residente@condohub.cl")
            self.assertEqual(fotos["DESPUES"].subido_por.email, "conserje@condohub.cl")
            for foto in fotos.values():
                self.assertTrue(os.path.exists(os.path.join(carpeta, foto.imagen.name)))
        # Solo el resuelto lleva fotos: los otros dos incidentes no.
        self.assertEqual(FotoIncidente.objects.exclude(incidente=resuelto).count(), 0)

    @override_settings(DEMO_FECHA_REFERENCIA=date(2026, 11, 16), FOTOS_INCIDENTES_HABILITADAS=False)
    def test_subida_apagada_no_genera_fotos(self):
        # Evita que la demo escriba fotos que se perderían al reiniciar cuando no hay almacenamiento persistente.
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(FotoIncidente.objects.count(), 0)

    def test_carga_normal_no_trae_fotos(self):
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(FotoIncidente.objects.count(), 0)
