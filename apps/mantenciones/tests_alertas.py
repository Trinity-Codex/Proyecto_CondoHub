"""Pruebas de las alertas de vencimiento y de los certificados de mantención (Issue #123, segundo PR)."""
from datetime import timedelta
from io import BytesIO, StringIO

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.condominios.models import Membresia
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.notificaciones.models import Notificacion

from .alertas import enviar_alertas
from .models import AlertaEnviada, EjecucionMantencion
from .tests import crear_mantencion

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def imagen_con_exif(formato="JPEG"):
    """Una imagen mínima; en JPEG lleva un EXIF (marca de cámara) que debe desaparecer al guardarse."""
    salida = BytesIO()
    imagen = Image.new("RGB", (8, 8), "red")
    if formato == "JPEG":
        exif = Image.Exif()
        exif[0x010F] = "CamaraSecreta"
        imagen.save(salida, "JPEG", exif=exif)
    else:
        imagen.save(salida, "PNG")
    return salida.getvalue()


class AlertasTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.hoy = timezone.localdate()

    def test_avisa_a_los_administradores_de_una_mantencion_por_vencer(self):
        crear_mantencion(self.e.condominio, dias=5)
        self.assertEqual(enviar_alertas(self.hoy), 1)
        avisos = Notificacion.objects.filter(usuario=self.e.administrador)
        self.assertEqual(avisos.count(), 1)
        self.assertIn("por vencer", avisos.get().titulo)
        # Comité, conserje y residente no son destinatarios.
        for otro in (self.e.comite, self.e.conserje, self.e.residente):
            self.assertFalse(Notificacion.objects.filter(usuario=otro).exists())

    def test_tambien_avisa_si_ya_vencio_sin_aviso_previo(self):
        crear_mantencion(self.e.condominio, dias=-3)
        self.assertEqual(enviar_alertas(self.hoy), 1)
        self.assertIn("vencida", Notificacion.objects.get(usuario=self.e.administrador).titulo)

    def test_una_mantencion_al_dia_no_avisa(self):
        crear_mantencion(self.e.condominio, dias=200)
        self.assertEqual(enviar_alertas(self.hoy), 0)
        self.assertFalse(Notificacion.objects.exists())

    def test_correrlo_dos_veces_no_repite_el_aviso(self):
        crear_mantencion(self.e.condominio, dias=5)
        enviar_alertas(self.hoy)
        self.assertEqual(enviar_alertas(self.hoy), 0)
        # Ni al pasar a vencida: es el mismo ciclo (misma fecha de vencimiento).
        self.assertEqual(enviar_alertas(self.hoy + timedelta(days=30)), 0)
        self.assertEqual(Notificacion.objects.count(), 1)

    def test_el_ciclo_siguiente_vuelve_a_avisar(self):
        m = crear_mantencion(self.e.condominio, dias=5, meses=1)
        enviar_alertas(self.hoy)
        m.registrar_ejecucion(self.e.administrador, self.hoy)
        m.refresh_from_db()
        self.assertEqual(enviar_alertas(self.hoy), 0)  # la nueva fecha aún está lejos
        self.assertEqual(enviar_alertas(m.proxima_fecha - timedelta(days=3)), 1)
        self.assertEqual(AlertaEnviada.objects.filter(mantencion=m).count(), 2)

    def test_solo_los_administradores_del_mismo_condominio(self):
        crear_mantencion(self.e.ajeno, dias=2)
        admin_ajeno = crear_usuario("admin_ajeno@ejemplo.cl")
        Membresia.objects.create(usuario=admin_ajeno, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        enviar_alertas(self.hoy)
        self.assertTrue(Notificacion.objects.filter(usuario=admin_ajeno).exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.e.administrador).exists())

    def test_tambien_sale_por_correo(self):
        crear_mantencion(self.e.condominio, dias=5)
        with self.captureOnCommitCallbacks(execute=True):
            enviar_alertas(self.hoy)
        self.assertTrue(any("Mantención" in c.subject for c in mail.outbox))

    def test_el_comando_acepta_fecha_y_es_idempotente(self):
        crear_mantencion(self.e.condominio, dias=5)
        call_command("enviar_alertas_mantenciones", "--fecha", self.hoy.isoformat(), stdout=StringIO())
        call_command("enviar_alertas_mantenciones", "--fecha", self.hoy.isoformat(), stdout=StringIO())
        self.assertEqual(Notificacion.objects.count(), 1)


class TarjetaDelPanelTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        crear_mantencion(self.e.condominio, "Red húmeda", dias=-2)
        crear_mantencion(self.e.condominio, "Ascensores", dias=300)

    def test_el_administrador_ve_solo_lo_que_requiere_atencion(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertContains(respuesta, "Mantenciones por atender")
        self.assertContains(respuesta, "Red húmeda")
        self.assertNotContains(respuesta, "Ascensores")

    def test_otros_roles_no_la_ven(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            self.assertNotContains(self.client.get(reverse("core:inicio")), "Mantenciones por atender")


class CertificadoTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.m = crear_mantencion(self.e.condominio, dias=-1)
        self.url = reverse("mantenciones:ejecucion", args=[self.m.pk])
        self.client.force_login(self.e.administrador)

    def subir(self, nombre, contenido, tipo="application/octet-stream"):
        return self.client.post(self.url, {
            "fecha": timezone.localdate().isoformat(), "certificado": SimpleUploadedFile(nombre, contenido, tipo),
        })

    def test_acepta_un_pdf_y_lo_guarda_con_nombre_al_azar(self):
        self.assertRedirects(self.subir("Mi certificado.pdf", PDF), reverse("mantenciones:lista"))
        nombre = EjecucionMantencion.objects.get().certificado.name
        self.assertTrue(nombre.startswith("mantenciones/certificados/") and nombre.endswith(".pdf"))
        self.assertNotIn("certificado.pdf", nombre.replace("certificados/", ""))

    def test_la_imagen_se_guarda_sin_exif(self):
        self.subir("foto.jpg", imagen_con_exif())
        ejecucion = EjecucionMantencion.objects.get()
        with ejecucion.certificado.open("rb") as archivo:
            guardado = archivo.read()
        self.assertNotIn(b"CamaraSecreta", guardado)
        self.assertEqual(Image.open(BytesIO(guardado)).format, "JPEG")

    def test_rechaza_lo_que_no_es_jpg_png_ni_pdf_reales(self):
        for nombre, contenido in [("a.pdf", b"no soy un pdf"), ("b.jpg", b"texto"), ("c.svg", b"<svg onload=alert(1)/>"),
                                  ("d.png", b"%PD")]:
            respuesta = self.subir(nombre, contenido)
            self.assertEqual(respuesta.status_code, 200, nombre)
            self.assertContains(respuesta, "JPG, PNG o PDF")
        self.assertFalse(EjecucionMantencion.objects.exists())

    def test_rechaza_mas_de_5_mb(self):
        respuesta = self.subir("grande.pdf", PDF + b"0" * (5 * 1024 * 1024))
        self.assertContains(respuesta, "5 MB")
        self.assertFalse(EjecucionMantencion.objects.exists())

    def test_sin_certificado_sigue_funcionando(self):
        self.client.post(self.url, {"fecha": timezone.localdate().isoformat()})
        self.assertFalse(EjecucionMantencion.objects.get().certificado)

    def test_descarga_por_rol_y_condominio(self):
        self.subir("a.pdf", PDF)
        url = reverse("mantenciones:certificado", args=[EjecucionMantencion.objects.get().pk])
        for usuario in (self.e.administrador, self.e.comite, self.e.conserje):
            self.client.force_login(usuario)
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn("attachment", respuesta["Content-Disposition"])
            self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
            b"".join(respuesta.streaming_content)  # leer la respuesta la cierra sin cerrar la conexión de MySQL
        self.client.force_login(self.e.residente)
        self.assertEqual(self.client.get(url).status_code, 403)
        # Un administrador de otro condominio no ve ni que existe.
        ajeno = crear_usuario("admin_ajeno@ejemplo.cl")
        Membresia.objects.create(usuario=ajeno, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_la_ejecucion_con_certificado_queda_en_auditoria(self):
        from apps.auditoria.models import RegistroAuditoria

        self.subir("a.pdf", PDF)
        self.assertTrue(RegistroAuditoria.objects.filter(despues__con_certificado=True).exists())


class DemoSinAdjuntosTest(TestCase):
    """En la demo de Render se puede registrar la ejecución, pero no adjuntar archivos."""

    def test_con_adjunto_se_bloquea_y_sin_adjunto_pasa(self):
        from apps.core.middleware_demo import SoloLecturaDemoMiddleware

        e = crear_escenario()
        m = crear_mantencion(e.condominio, dias=-1)
        url = reverse("mantenciones:ejecucion", args=[m.pk])
        hoy = timezone.localdate().isoformat()
        with self.modify_settings(MIDDLEWARE={"append": "apps.core.middleware_demo.SoloLecturaDemoMiddleware"}):
            self.client.force_login(e.administrador)
            con = self.client.post(url, {"fecha": hoy, "certificado": SimpleUploadedFile("a.pdf", PDF)})
            self.assertEqual(con.status_code, 403)
            sin = self.client.post(url, {"fecha": hoy})
            self.assertEqual(sin.status_code, 302)
        self.assertEqual(EjecucionMantencion.objects.count(), 1)
        self.assertFalse(EjecucionMantencion.objects.get().certificado)
