"""Pruebas de auditoria: página provisional y permisos por rol (contrato C0, #62)."""
from datetime import date
from decimal import Decimal

from django.contrib import admin as admin_django
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import RegistroAuditoria, RegistroInmutable
from apps.auditoria.servicios import Accion, registrar
from apps.core.pruebas import crear_escenario


class PaginaProvisionalTest(TestCase):
    """Solo entra el administrador (200); los demás roles reciben 403 y sin sesión se pide iniciarla."""

    def setUp(self):
        self.e = crear_escenario()
        self.url = reverse("auditoria:inicio")

    def test_quien_puede_entrar(self):
        esperados = [
            (self.e.administrador, 200),
            (self.e.comite, 403),
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

    def test_el_registro_sobrevive_si_se_borra_el_usuario(self):
        registro = registrar(self.e.administrador, self.e.condominio, Accion.CREAR, self.e.condominio)
        id_usuario, nombre = registro.usuario_id, registro.usuario_nombre
        self.e.administrador.delete()
        registro.refresh_from_db()
        # El número de usuario se conserva como referencia y el nombre queda como estaba.
        self.assertEqual(registro.usuario_id, id_usuario)
        self.assertEqual(registro.usuario_nombre, nombre)
