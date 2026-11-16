"""Pruebas de auditoria: permisos por rol (C0, #62), lista con filtros (#27) y registro inmutable."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin as admin_django
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import RegistroAuditoria, RegistroInmutable
from apps.auditoria.servicios import Accion, registrar
from apps.core.pruebas import crear_escenario


def _registrar_el(cuando, usuario, condominio, accion=Accion.CREAR):
    """
    Crea un registro con `creado` en `cuando`. `creado` es auto_now_add y el modelo es inmutable,
    así que no se puede editar la fecha después: se simula el reloj solo durante la creación.
    """
    with patch("django.utils.timezone.now", return_value=cuando):
        return registrar(usuario, condominio, accion, condominio)


def _fecha(dia, hora=12, minuto=0):
    """Fecha con zona horaria del proyecto: el filtro compara por día local, no por UTC."""
    return datetime(2026, 3, dia, hora, minuto, tzinfo=timezone.get_current_timezone())


class PaginaProvisionalTest(TestCase):
    """Administrador y comité entran (200); conserje y residente reciben 403 y sin sesión se pide iniciarla."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("auditoria:inicio")

    def test_quien_puede_entrar(self):
        esperados = [
            (self.e.administrador, 200),
            (self.e.comite, 200),
            (self.e.conserje, 403),
            (self.e.residente, 403),
        ]
        for usuario, esperado in esperados:
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, esperado)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(
            respuesta, reverse("cuentas:iniciar_sesion") + "?next=" + self.url, fetch_redirect_response=False
        )

    def test_el_menu_tiene_el_enlace(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("core:inicio")), self.url)


class ListaAuditoriaTest(TestCase):
    """La lista se limita al condominio, filtra por fecha y usuario, y es de solo lectura."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("auditoria:inicio")
        # Registros del condominio propio: dos días distintos y dos usuarios.
        self.r_admin = _registrar_el(_fecha(10, 0, 0), self.e.administrador, self.e.condominio, Accion.MODIFICAR)
        self.r_comite = _registrar_el(_fecha(12, 23, 59), self.e.comite, self.e.condominio, Accion.ANULAR)
        # Registros de "Ajeno": otro usuario, y fechas (5 y 20) que el condominio propio no usa.
        self.r_ajeno = _registrar_el(_fecha(5), self.e.residente_ajeno, self.e.ajeno)
        self.r_ajeno_fecha = _registrar_el(_fecha(20), self.e.administrador, self.e.ajeno)

    def ids(self, respuesta):
        return {r.pk for r in respuesta.context["registros"]}

    def test_administrador_y_comite_ven_solo_su_condominio(self):
        for usuario in (self.e.administrador, self.e.comite):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                respuesta = self.client.get(self.url)
                self.assertEqual(self.ids(respuesta), {self.r_admin.pk, self.r_comite.pk})
                self.assertContains(respuesta, "Anular")

    def test_estado_vacio(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"desde": "2026-03-15", "hasta": "2026-03-16"})
        self.assertContains(respuesta, "No hay registros de auditoría")

    def test_filtro_por_fechas_con_bordes_inclusivos(self):
        self.client.force_login(self.e.administrador)
        casos = [
            ({"desde": "2026-03-12"}, {self.r_comite.pk}),  # borde: 23:59 del día 12 entra
            ({"hasta": "2026-03-10"}, {self.r_admin.pk}),  # borde: 00:00 del día 10 entra
            ({"desde": "2026-03-10", "hasta": "2026-03-12"}, {self.r_admin.pk, self.r_comite.pk}),
            ({"desde": "2026-03-11", "hasta": "2026-03-11"}, set()),
        ]
        for filtros, esperado in casos:
            with self.subTest(filtros=filtros):
                self.assertEqual(self.ids(self.client.get(self.url, filtros)), esperado)

    def test_filtro_por_usuario(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"usuario": str(self.e.comite.pk)})
        self.assertEqual(self.ids(respuesta), {self.r_comite.pk})

    def test_filtrar_por_usuario_de_otro_condominio_no_devuelve_sus_registros(self):
        # residente_ajeno solo tiene registros en "Ajeno": no es una opción válida aquí.
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"usuario": str(self.e.residente_ajeno.pk)})
        self.assertFalse(self.ids(respuesta) & {self.r_ajeno.pk, self.r_ajeno_fecha.pk})
        self.assertTrue(respuesta.context["filtro"].errors)

    def test_filtrar_por_fechas_de_otro_condominio_no_devuelve_sus_registros(self):
        self.client.force_login(self.e.comite)
        for filtros in ({"desde": "2026-03-20", "hasta": "2026-03-20"}, {"desde": "2026-03-05", "hasta": "2026-03-05"}):
            with self.subTest(filtros=filtros):
                self.assertEqual(self.ids(self.client.get(self.url, filtros)), set())

    def test_desde_mayor_que_hasta_es_error_y_no_filtra(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"desde": "2026-03-12", "hasta": "2026-03-10"})
        self.assertTrue(respuesta.context["filtro"].non_field_errors())
        self.assertEqual(self.ids(respuesta), {self.r_admin.pk, self.r_comite.pk})

    def test_la_paginacion_conserva_los_filtros(self):
        for _ in range(50):
            registrar(self.e.administrador, self.e.condominio, Accion.CREAR, self.e.condominio)
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(self.url, {"usuario": str(self.e.administrador.pk)})
        self.assertEqual(len(respuesta.context["registros"]), 50)
        self.assertContains(respuesta, f"usuario={self.e.administrador.pk}&amp;page=2")

    def test_post_responde_405_y_no_cambia_los_registros(self):
        self.client.force_login(self.e.administrador)
        antes = RegistroAuditoria.objects.count()
        self.assertEqual(self.client.post(self.url, {"accion": "crear"}).status_code, 405)
        self.assertEqual(RegistroAuditoria.objects.count(), antes)

    def test_la_pagina_no_tiene_enlaces_de_edicion_ni_de_borrado(self):
        self.client.force_login(self.e.administrador)
        html = self.client.get(self.url).content.decode().lower()
        for texto in ("editar", "borrar", "eliminar", "/admin/auditoria"):
            with self.subTest(texto=texto):
                self.assertNotIn(texto, html)


class RegistroInmutableTest(TestCase):
    """Un registro se inserta una vez; editarlo o borrarlo, por cualquier vía, falla y no cambia la fila."""

    def setUp(self):
        self.e = crear_escenario()
        self.registro = registrar(self.e.administrador, self.e.condominio, Accion.MODIFICAR, self.e.condominio)

    def test_no_se_puede_editar_con_save(self):
        self.registro.accion = "otra"
        with self.assertRaises(RegistroInmutable):
            self.registro.save()
        self.assertEqual(RegistroAuditoria.objects.get(pk=self.registro.pk).accion, Accion.MODIFICAR)

    def test_no_se_puede_borrar_con_delete(self):
        with self.assertRaises(RegistroInmutable):
            self.registro.delete()
        self.assertTrue(RegistroAuditoria.objects.filter(pk=self.registro.pk).exists())

    def test_no_se_puede_editar_ni_borrar_en_bloque(self):
        with self.assertRaises(RegistroInmutable):
            RegistroAuditoria.objects.filter(pk=self.registro.pk).update(accion="otra")
        with self.assertRaises(RegistroInmutable):
            RegistroAuditoria.objects.filter(pk=self.registro.pk).delete()
        self.assertEqual(RegistroAuditoria.objects.get(pk=self.registro.pk).accion, Accion.MODIFICAR)

    def test_no_se_puede_reemplazar_con_un_objeto_nuevo_con_el_mismo_id(self):
        # Un objeto nuevo con el id de otro haría un UPDATE y reemplazaría el original.
        copia = RegistroAuditoria(
            pk=self.registro.pk, condominio_id=self.e.condominio.pk, condominio_nombre="x", usuario_nombre="x",
            accion="otra", objeto_tipo="x", objeto_id="1",
        )
        with self.assertRaises(RegistroInmutable):
            copia.save()
        self.assertEqual(RegistroAuditoria.objects.get(pk=self.registro.pk).accion, Accion.MODIFICAR)

    def test_el_admin_no_ofrece_cambiar_ni_borrar(self):
        ma = admin_django.site._registry[RegistroAuditoria]
        peticion = type("Peticion", (), {"user": self.e.administrador})()
        self.assertFalse(ma.has_change_permission(peticion, self.registro))
        self.assertFalse(ma.has_delete_permission(peticion, self.registro))
        self.assertFalse(ma.has_add_permission(peticion))


class RegistrarTest(TestCase):
    """`registrar()` guarda todos los campos y devuelve el registro."""

    def setUp(self):
        self.e = crear_escenario()

    def test_guarda_los_campos_y_devuelve_el_registro(self):
        antes_del_registro = timezone.now()
        registro = registrar(self.e.administrador, self.e.condominio, Accion.CAMBIAR_ROL, self.e.condominio)
        self.assertIsInstance(registro, RegistroAuditoria)
        self.assertEqual(registro.condominio_id, self.e.condominio.pk)
        self.assertEqual(registro.usuario_id, self.e.administrador.pk)
        self.assertEqual(registro.usuario_nombre, self.e.administrador.get_full_name() or self.e.administrador.get_username())
        self.assertEqual(registro.accion, Accion.CAMBIAR_ROL)
        self.assertEqual(registro.condominio_nombre, self.e.condominio.nombre)
        self.assertEqual(registro.objeto_tipo, "condominio")
        self.assertEqual(registro.objeto_id, str(self.e.condominio.pk))
        self.assertGreaterEqual(registro.creado, antes_del_registro)

    def test_solo_guarda_los_campos_que_cambian(self):
        registro = registrar(
            self.e.administrador,
            self.e.condominio,
            Accion.MODIFICAR,
            self.e.condominio,
            antes={"nombre": "Prueba", "comuna": "Santiago"},
            despues={"nombre": "Prueba", "comuna": "Providencia"},
        )
        self.assertEqual(registro.antes, {"comuna": "Santiago"})
        self.assertEqual(registro.despues, {"comuna": "Providencia"})

    def test_sin_valores_quedan_nulos(self):
        registro = registrar(self.e.administrador, self.e.condominio, Accion.CREAR, self.e.condominio)
        self.assertIsNone(registro.antes)
        self.assertIsNone(registro.despues)

    def test_comando_sin_usuario(self):
        registro = registrar(None, self.e.condominio, Accion.CREAR, self.e.condominio)
        self.assertIsNone(registro.usuario_id)
        self.assertEqual(registro.usuario_nombre, "Sistema")

    def test_valores_con_fecha_y_decimal_se_guardan_como_json(self):
        registro = registrar(
            self.e.administrador,
            self.e.condominio,
            Accion.MODIFICAR,
            self.e.condominio,
            antes={"monto": Decimal("1.50")},
            despues={"monto": Decimal("2.75"), "fecha": date(2026, 11, 8)},
        )
        registro.refresh_from_db()
        self.assertEqual(registro.despues["fecha"], "2026-11-08")

    def test_si_nada_cambio_los_valores_quedan_nulos(self):
        registro = registrar(
            self.e.administrador, self.e.condominio, Accion.MODIFICAR, self.e.condominio,
            antes={"nombre": "Prueba"}, despues={"nombre": "Prueba"},
        )
        self.assertIsNone(registro.antes)
        self.assertIsNone(registro.despues)

    def test_un_dato_borrado_queda_registrado(self):
        # Pasar de "sin clave" a None (o al revés) es un cambio: borra un dato personal.
        registro = registrar(
            self.e.administrador, self.e.condominio, Accion.MODIFICAR, self.e.condominio,
            antes={"rut": "11.111.111-1"}, despues={"rut": None},
        )
        self.assertEqual(registro.despues, {"rut": None})
        registro = registrar(
            self.e.administrador, self.e.condominio, Accion.MODIFICAR, self.e.condominio,
            antes={}, despues={"rut": None},
        )
        self.assertEqual(registro.despues, {"rut": None})

    def test_objeto_sin_id_se_rechaza(self):
        # Después de delete() Django deja pk=None; se guardaría "None" como id.
        sin_id = type(self.e.condominio)(nombre="Sin guardar")
        with self.assertRaises(ValueError):
            registrar(self.e.administrador, self.e.condominio, Accion.ELIMINAR, sin_id)
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_accion_desconocida_se_rechaza(self):
        with self.assertRaises(ValueError):
            registrar(self.e.administrador, self.e.condominio, "anulado", self.e.condominio)

    def test_nombre_largo_se_recorta(self):
        self.e.administrador.first_name = "A" * 150
        self.e.administrador.last_name = "B" * 150
        registro = registrar(self.e.administrador, self.e.condominio, Accion.CREAR, self.e.condominio)
        registro.refresh_from_db()
        self.assertEqual(len(registro.usuario_nombre), 150)

    def test_el_registro_sobrevive_si_se_borra_el_usuario(self):
        registro = registrar(self.e.administrador, self.e.condominio, Accion.CREAR, self.e.condominio)
        id_usuario, nombre = registro.usuario_id, registro.usuario_nombre
        self.e.administrador.delete()
        registro.refresh_from_db()
        # El número de usuario se conserva como referencia y el nombre queda como estaba.
        self.assertEqual(registro.usuario_id, id_usuario)
        self.assertEqual(registro.usuario_nombre, nombre)
