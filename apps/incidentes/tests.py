"""Pruebas de incidentes (RF07, RF08) y sus notificaciones (RF10)."""
import os
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Membresia
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.notificaciones.models import Notificacion

from .forms import MAX_BYTES_FOTO, MAX_FOTOS_POR_INCIDENTE
from .models import FotoIncidente, Incidente


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


def imagen(nombre="foto.jpg", formato="JPEG"):
    """Imagen real mínima, lista para subir (el formato lo decide Pillow, no el nombre)."""
    contenido = BytesIO()
    Image.new("RGB", (20, 20), "red").save(contenido, format=formato)
    return SimpleUploadedFile(nombre, contenido.getvalue())


class FotosIncidenteTest(TestCase):
    """Fotos de respaldo antes/después (Issue #122): subida, límites, permisos, aislamiento y auditoría."""

    def setUp(self):
        self.e = crear_escenario()
        # No hay MEDIA_ROOT en settings (lo trae #116): los archivos de prueba van a una carpeta temporal que se borra sola.
        carpeta = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=carpeta))
        self.media = carpeta
        self.incidente = Incidente.objects.create(
            condominio=self.e.condominio, reportado_por=self.e.residente, categoria=Incidente.Categoria.ASEO,
            titulo="Basurero sucio", descripcion="x", estado=Incidente.Estado.RESUELTO,
        )

    def foto(self, etapa=FotoIncidente.Etapa.ANTES, incidente=None, usuario=None):
        return FotoIncidente.subir(
            incidente or self.incidente, [imagen()], etapa, usuario or self.e.residente
        )[0]

    def reportar(self, *archivos, usuario=None):
        self.client.force_login(usuario or self.e.residente)
        return self.client.post(reverse("incidentes:nuevo"), {
            "categoria": Incidente.Categoria.MANTENCION, "titulo": "Fuga", "descripcion": "Gotea.",
            "fotos": list(archivos),
        })

    def subir_despues(self, usuario, *archivos, incidente=None):
        self.client.force_login(usuario)
        incidente = incidente or self.incidente
        return self.client.post(reverse("incidentes:foto_subir", args=[incidente.pk]), {"fotos": list(archivos)}, follow=True)

    def mensajes(self, respuesta):
        return [str(m) for m in respuesta.context["messages"]]

    def auditoria(self, accion):
        return RegistroAuditoria.objects.filter(objeto_tipo="fotoincidente", accion=accion)

    # --- subida ---

    def test_residente_sube_fotos_antes_al_reportar(self):
        respuesta = self.reportar(imagen("a.jpg"), imagen("b.png", "PNG"))
        incidente = Incidente.objects.latest("pk")
        self.assertRedirects(respuesta, incidente.get_absolute_url())
        fotos = list(incidente.fotos.all())
        self.assertEqual(len(fotos), 2)
        for foto in fotos:
            self.assertEqual(foto.etapa, FotoIncidente.Etapa.ANTES)
            self.assertEqual(foto.subido_por, self.e.residente)
            # Nombre generado y dentro de incidentes/<condominio_id>/: no queda el nombre que puso el usuario.
            carpeta, nombre = os.path.split(foto.imagen.name)
            self.assertEqual(carpeta, f"incidentes/{self.e.condominio.pk}")
            self.assertNotIn(nombre.split(".")[0], ("a", "b"))
            self.assertTrue(os.path.exists(os.path.join(self.media, foto.imagen.name)))
        self.assertEqual(self.auditoria("crear").count(), 2)

    def test_reportar_sin_fotos_sigue_funcionando(self):
        self.reportar()
        self.assertEqual(Incidente.objects.latest("pk").fotos.count(), 0)

    def test_administrador_y_conserje_suben_fotos_despues(self):
        for usuario in (self.e.administrador, self.e.conserje):
            respuesta = self.subir_despues(usuario, imagen())
            self.assertIn("Se subieron 1 foto(s) al incidente", self.mensajes(respuesta)[0])
        fotos = self.incidente.fotos.all()
        self.assertEqual([f.etapa for f in fotos], [FotoIncidente.Etapa.DESPUES] * 2)
        self.assertEqual([f.subido_por for f in fotos], [self.e.administrador, self.e.conserje])

    def test_residente_y_comite_no_suben_fotos_despues(self):
        for usuario in (self.e.residente, self.e.comite):
            respuesta = self.subir_despues(usuario, imagen())
            self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(FotoIncidente.objects.count(), 0)

    def test_subir_a_incidente_de_otro_condominio_da_404(self):
        ajeno = Incidente.objects.create(
            condominio=self.e.ajeno, reportado_por=self.e.residente_ajeno, categoria=Incidente.Categoria.OTRO,
            titulo="Ajeno", descripcion="x",
        )
        self.assertEqual(self.subir_despues(self.e.administrador, imagen(), incidente=ajeno).status_code, 404)
        self.assertEqual(FotoIncidente.objects.count(), 0)

    # --- rechazos ---

    def test_rechaza_txt_renombrado_a_jpg(self):
        falso = SimpleUploadedFile("nota.jpg", b"esto es texto, no una imagen")
        respuesta = self.reportar(falso)
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        self.assertIn("«nota.jpg»: no es una imagen JPG o PNG válida.", respuesta.context["form"].errors["fotos"])
        self.assertFalse(Incidente.objects.filter(titulo="Fuga").exists())  # nada queda a medias

    def test_rechaza_extension_que_no_es_jpg_ni_png(self):
        respuesta = self.reportar(imagen("animada.gif", "GIF"))
        self.assertIn("«animada.gif»: solo se aceptan imágenes JPG o PNG.", respuesta.context["form"].errors["fotos"])

    def test_rechaza_mas_de_5_mb(self):
        pesada = SimpleUploadedFile("grande.jpg", b"x" * (MAX_BYTES_FOTO + 1))
        respuesta = self.reportar(pesada)
        self.assertIn("«grande.jpg»: pesa 5.0 MB y el máximo es 5 MB.", respuesta.context["form"].errors["fotos"])
        self.assertEqual(FotoIncidente.objects.count(), 0)

    def test_rechaza_la_foto_numero_11(self):
        for _ in range(MAX_FOTOS_POR_INCIDENTE):
            self.foto(FotoIncidente.Etapa.ANTES)
        respuesta = self.subir_despues(self.e.administrador, imagen())
        self.assertIn("Cada incidente admite hasta 10 fotos", self.mensajes(respuesta)[0])
        self.assertEqual(self.incidente.fotos.count(), MAX_FOTOS_POR_INCIDENTE)

    def test_rechaza_11_fotos_en_un_mismo_reporte(self):
        respuesta = self.reportar(*[imagen() for _ in range(MAX_FOTOS_POR_INCIDENTE + 1)])
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("quieres agregar 11", respuesta.context["form"].errors["fotos"][0])
        self.assertFalse(Incidente.objects.filter(titulo="Fuga").exists())

    # --- borrar ---

    def test_administrador_y_conserje_borran_y_queda_en_auditoria(self):
        for usuario in (self.e.administrador, self.e.conserje):
            foto = self.foto()
            ruta = os.path.join(self.media, foto.imagen.name)
            self.client.force_login(usuario)
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.client.post(reverse("incidentes:foto_borrar", args=[foto.pk]))
            self.assertRedirects(respuesta, self.incidente.get_absolute_url())
            self.assertFalse(FotoIncidente.objects.filter(pk=foto.pk).exists())
            self.assertFalse(os.path.exists(ruta))  # el archivo también sale del disco
            baja = self.auditoria("eliminar").get(objeto_id=str(foto.pk))
            self.assertEqual(baja.usuario_id, usuario.pk)
            self.assertEqual(baja.antes, {"incidente": self.incidente.pk, "etapa": "ANTES"})

    def test_residente_y_comite_no_borran(self):
        foto = self.foto()
        for usuario in (self.e.residente, self.e.comite):
            self.client.force_login(usuario)
            self.assertEqual(self.client.post(reverse("incidentes:foto_borrar", args=[foto.pk])).status_code, 403)
        self.assertTrue(FotoIncidente.objects.filter(pk=foto.pk).exists())
        self.assertEqual(self.auditoria("eliminar").count(), 0)

    def test_no_borra_fotos_de_otro_condominio(self):
        foto = self.foto()
        # Administrador de OTRO condominio: tiene el rol, pero la foto no es de su condominio activo.
        otro_admin = crear_usuario("admin@ajeno.cl")
        Membresia.objects.create(usuario=otro_admin, condominio=self.e.ajeno, rol=Membresia.Rol.ADMINISTRADOR)
        self.client.force_login(otro_admin)
        self.assertEqual(self.client.post(reverse("incidentes:foto_borrar", args=[foto.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("incidentes:foto", args=[foto.pk])).status_code, 404)
        self.assertTrue(FotoIncidente.objects.filter(pk=foto.pk).exists())

    # --- quién ve (galería y archivo por URL directa) ---

    def test_ven_el_archivo_administrador_comite_conserje_y_el_residente_que_reporto(self):
        foto = self.foto()
        for usuario in (self.e.administrador, self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            respuesta = self.client.get(reverse("incidentes:foto", args=[foto.pk]))
            self.assertEqual(respuesta.status_code, 200, usuario.email)
            self.assertEqual(respuesta["Content-Type"], "image/jpeg")
            self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
            self.assertIn("private", respuesta["Cache-Control"])
            respuesta.close()

    def test_otro_residente_no_ve_el_archivo_por_url_directa(self):
        foto = self.foto()
        self.client.force_login(self.e.residente_b)  # mismo condominio, pero no reportó el incidente
        self.assertEqual(self.client.get(reverse("incidentes:foto", args=[foto.pk])).status_code, 404)

    def test_residente_de_otro_condominio_no_ve_el_archivo(self):
        foto = self.foto()
        self.client.force_login(self.e.residente_ajeno)
        self.assertEqual(self.client.get(reverse("incidentes:foto", args=[foto.pk])).status_code, 404)

    def test_sin_sesion_el_archivo_lleva_al_login(self):
        foto = self.foto()
        respuesta = self.client.get(reverse("incidentes:foto", args=[foto.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("iniciar-sesion", respuesta["Location"])

    def test_el_archivo_no_se_sirve_por_media_url(self):
        foto = self.foto()
        self.client.force_login(self.e.administrador)
        html = self.client.get(self.incidente.get_absolute_url()).content.decode()
        self.assertIn(reverse("incidentes:foto", args=[foto.pk]), html)
        self.assertNotIn(foto.imagen.url, html)

    def test_detalle_muestra_antes_y_despues_con_fecha_y_autor(self):
        antes = self.foto(FotoIncidente.Etapa.ANTES, usuario=self.e.residente)
        despues = self.foto(FotoIncidente.Etapa.DESPUES, usuario=self.e.conserje)
        # El residente que reportó ve ambas etapas de su incidente resuelto.
        self.client.force_login(self.e.residente)
        respuesta = self.client.get(self.incidente.get_absolute_url())
        self.assertEqual(list(respuesta.context["fotos_antes"]), [antes])
        self.assertEqual(list(respuesta.context["fotos_despues"]), [despues])
        self.assertContains(respuesta, "Fotos de respaldo")
        # La plantilla muestra la hora local, no la UTC con que se guarda.
        self.assertContains(respuesta, f"{timezone.localtime(despues.fecha_subida):%d-%m-%Y %H:%M} · conserje")
        self.assertContains(respuesta, f"{timezone.localtime(antes.fecha_subida):%d-%m-%Y %H:%M} · residente")
        # Sin permiso de gestión no hay botón de borrar ni formulario de subida.
        self.assertNotContains(respuesta, "foto_borrar")
        self.assertNotContains(respuesta, reverse("incidentes:foto_subir", args=[self.incidente.pk]))

    def test_gestion_ve_boton_de_borrar_y_formulario_de_subida(self):
        foto = self.foto()
        self.client.force_login(self.e.conserje)
        respuesta = self.client.get(self.incidente.get_absolute_url())
        self.assertContains(respuesta, reverse("incidentes:foto_borrar", args=[foto.pk]))
        self.assertContains(respuesta, reverse("incidentes:foto_subir", args=[self.incidente.pk]))

    def test_residente_ajeno_no_ve_la_galeria_de_otro_residente(self):
        self.foto()
        self.client.force_login(self.e.residente_b)
        self.assertEqual(self.client.get(self.incidente.get_absolute_url()).status_code, 404)

    # --- auditoría ---

    def test_la_subida_registra_quien_incidente_y_etapa(self):
        foto = self.foto(FotoIncidente.Etapa.DESPUES, usuario=self.e.conserje)
        registro = self.auditoria("crear").get(objeto_id=str(foto.pk))
        self.assertEqual(registro.usuario_id, self.e.conserje.pk)
        self.assertEqual(registro.condominio_id, self.e.condominio.pk)
        self.assertEqual(registro.despues, {"incidente": self.incidente.pk, "etapa": "DESPUES"})
