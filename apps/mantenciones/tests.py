"""Pruebas de mantenciones (Issue #123): estados, fechas, permisos por rol, aislamiento y auditoría."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import RegistroAuditoria
from apps.condominios.models import Condominio
from apps.core.pruebas import crear_escenario
from apps.proveedores.models import Proveedor

from . import demo
from .models import EjecucionMantencion, Mantencion, sumar_meses


def crear_mantencion(condominio, nombre="Recarga de extintores", dias=30, meses=12, **extra):
    """Una mantención cuya próxima fecha está `dias` días desde hoy (negativo = atrasada)."""
    return Mantencion.objects.create(
        condominio=condominio, nombre=nombre, frecuencia_meses=meses,
        proxima_fecha=timezone.localdate() + timedelta(days=dias), **extra,
    )


class SumarMesesTest(TestCase):
    """Suma de meses de calendario sin librerías externas."""

    def test_cambio_de_mes_y_de_anio(self):
        self.assertEqual(sumar_meses(date(2026, 11, 15), 1), date(2026, 12, 15))
        self.assertEqual(sumar_meses(date(2026, 12, 15), 1), date(2027, 1, 15))
        self.assertEqual(sumar_meses(date(2026, 3, 10), 6), date(2026, 9, 10))

    def test_fin_de_mes_se_ajusta_al_ultimo_dia(self):
        self.assertEqual(sumar_meses(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(sumar_meses(date(2026, 8, 31), 1), date(2026, 9, 30))
        self.assertEqual(sumar_meses(date(2026, 12, 31), 2), date(2027, 2, 28))

    def test_anio_bisiesto(self):
        self.assertEqual(sumar_meses(date(2028, 1, 31), 1), date(2028, 2, 29))
        self.assertEqual(sumar_meses(date(2028, 2, 29), 12), date(2029, 2, 28))
        self.assertEqual(sumar_meses(date(2028, 2, 29), 48), date(2032, 2, 29))


class EstadoTest(TestCase):
    """El estado se calcula respecto de una fecha; no se guarda."""

    def setUp(self):
        self.e = crear_escenario()
        self.hoy = date(2026, 11, 16)

    def mantencion(self, proxima, **extra):
        return Mantencion(condominio=self.e.condominio, nombre="X", frecuencia_meses=6, proxima_fecha=proxima, **extra)

    def test_vencida_por_vencer_y_al_dia(self):
        self.assertEqual(self.mantencion(self.hoy - timedelta(days=1)).estado_en(self.hoy), Mantencion.Estado.VENCIDA)
        self.assertEqual(self.mantencion(self.hoy).estado_en(self.hoy), Mantencion.Estado.POR_VENCER)
        self.assertEqual(self.mantencion(self.hoy + timedelta(days=15)).estado_en(self.hoy), Mantencion.Estado.POR_VENCER)
        self.assertEqual(self.mantencion(self.hoy + timedelta(days=16)).estado_en(self.hoy), Mantencion.Estado.AL_DIA)

    def test_la_anticipacion_por_defecto_es_15_dias(self):
        self.assertEqual(self.mantencion(self.hoy).dias_anticipacion, 15)

    def test_la_anticipacion_es_configurable_por_mantencion(self):
        proxima = self.hoy + timedelta(days=30)
        self.assertEqual(self.mantencion(proxima).estado_en(self.hoy), Mantencion.Estado.AL_DIA)
        self.assertEqual(self.mantencion(proxima, dias_anticipacion=30).estado_en(self.hoy), Mantencion.Estado.POR_VENCER)
        self.assertEqual(self.mantencion(proxima, dias_anticipacion=0).estado_en(self.hoy), Mantencion.Estado.AL_DIA)

    def test_el_estado_no_es_un_campo_guardado(self):
        self.assertNotIn("estado", [campo.name for campo in Mantencion._meta.get_fields()])

    def test_el_estado_de_hoy_usa_la_fecha_local(self):
        self.assertEqual(crear_mantencion(self.e.condominio, dias=-1).estado, Mantencion.Estado.VENCIDA)
        self.assertEqual(crear_mantencion(self.e.condominio, dias=5).estado, Mantencion.Estado.POR_VENCER)


class EjecucionTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def test_registrar_ejecucion_recalcula_la_proxima_fecha(self):
        m = Mantencion.objects.create(
            condominio=self.e.condominio, nombre="Ascensores", frecuencia_meses=1, proxima_fecha=date(2028, 1, 10),
        )
        hoy = timezone.localdate()
        # La próxima fecha parte de cuándo se HIZO, no de la que tocaba.
        respuesta = self.client.post(reverse("mantenciones:ejecucion", args=[m.pk]), {"fecha": hoy.isoformat(), "observacion": "Todo bien"})
        self.assertRedirects(respuesta, reverse("mantenciones:lista"))
        m.refresh_from_db()
        self.assertEqual(m.proxima_fecha, sumar_meses(hoy, 1))
        ejecucion = EjecucionMantencion.objects.get()
        self.assertEqual((ejecucion.mantencion, ejecucion.fecha, ejecucion.observacion, ejecucion.usuario),
                         (m, hoy, "Todo bien", self.e.administrador))

    def test_fin_de_mes_al_registrar(self):
        m = crear_mantencion(self.e.condominio, meses=1, dias=-3)
        m.registrar_ejecucion(self.e.administrador, date(2027, 1, 31))
        m.refresh_from_db()
        self.assertEqual(m.proxima_fecha, date(2027, 2, 28))

    def test_no_se_acepta_una_fecha_futura(self):
        m = crear_mantencion(self.e.condominio)
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.client.post(reverse("mantenciones:ejecucion", args=[m.pk]), {"fecha": manana.isoformat()})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(EjecucionMantencion.objects.exists())
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_la_ejecucion_queda_en_auditoria(self):
        m = crear_mantencion(self.e.condominio, meses=6, dias=-3)
        anterior = m.proxima_fecha
        m.registrar_ejecucion(self.e.administrador, date(2027, 1, 31))
        registro = RegistroAuditoria.objects.get()
        self.assertEqual(registro.accion, "crear")
        self.assertEqual(registro.objeto_tipo, "ejecucionmantencion")
        self.assertEqual(registro.usuario_id, self.e.administrador.pk)
        self.assertEqual(registro.condominio_id, self.e.condominio.pk)
        self.assertEqual(registro.antes, {"proxima_fecha": anterior.isoformat()})
        self.assertEqual(registro.despues, {"fecha_ejecucion": "2027-01-31", "proxima_fecha": "2027-07-31"})

    def test_si_la_auditoria_falla_no_queda_la_ejecucion(self):
        m = crear_mantencion(self.e.condominio)
        anterior = m.proxima_fecha
        m.condominio = None  # fuerza un error dentro de la transacción, después de crear la ejecución
        with self.assertRaises(Exception):
            m.registrar_ejecucion(self.e.administrador, timezone.localdate())
        self.assertFalse(EjecucionMantencion.objects.exists())
        self.assertEqual(Mantencion.objects.get(pk=m.pk).proxima_fecha, anterior)


class CrearYEditarTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)
        self.proveedor = Proveedor.objects.create(
            condominio=self.e.condominio, rut="76.123.456-0", razon_social="Ascensores Sur SpA", rubro="Ascensores",
        )

    def datos(self, **extra):
        base = {"nombre": "Revisión de red húmeda", "frecuencia_meses": 6, "proxima_fecha": "2026-12-01",
                "proveedor": self.proveedor.pk, "dias_anticipacion": 20}
        return {**base, **extra}

    def test_crear_pone_el_condominio_y_audita(self):
        respuesta = self.client.post(reverse("mantenciones:nueva"), self.datos())
        self.assertRedirects(respuesta, reverse("mantenciones:lista"))
        m = Mantencion.objects.get()
        self.assertEqual((m.condominio, m.nombre, m.frecuencia_meses, m.dias_anticipacion, m.proveedor),
                         (self.e.condominio, "Revisión de red húmeda", 6, 20, self.proveedor))
        registro = RegistroAuditoria.objects.get()
        self.assertEqual((registro.accion, registro.objeto_tipo, registro.objeto_id), ("crear", "mantencion", str(m.pk)))
        self.assertEqual(registro.usuario_id, self.e.administrador.pk)
        self.assertEqual(registro.despues["nombre"], "Revisión de red húmeda")

    def test_la_anticipacion_por_defecto_aparece_en_el_formulario(self):
        respuesta = self.client.get(reverse("mantenciones:nueva"))
        self.assertEqual(respuesta.context["form"]["dias_anticipacion"].value(), 15)

    def test_la_frecuencia_debe_ser_positiva(self):
        for malo in (0, -1):
            respuesta = self.client.post(reverse("mantenciones:nueva"), self.datos(frecuencia_meses=malo))
            self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Mantencion.objects.exists())

    def test_el_proveedor_es_opcional(self):
        self.client.post(reverse("mantenciones:nueva"), self.datos(proveedor=""))
        self.assertIsNone(Mantencion.objects.get().proveedor)

    def test_no_se_acepta_el_proveedor_de_otro_condominio(self):
        ajeno = Proveedor.objects.create(
            condominio=self.e.ajeno, rut="77.234.567-4", razon_social="Aseo Ajeno", rubro="Aseo",
        )
        respuesta = self.client.post(reverse("mantenciones:nueva"), self.datos(proveedor=ajeno.pk))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Mantencion.objects.exists())

    def test_editar_guarda_y_audita_solo_lo_que_cambia(self):
        m = crear_mantencion(self.e.condominio, dias=10, meses=12)
        respuesta = self.client.post(
            reverse("mantenciones:editar", args=[m.pk]),
            self.datos(nombre="Recarga de extintores", frecuencia_meses=6, proxima_fecha=m.proxima_fecha.isoformat(),
                       proveedor="", dias_anticipacion=15, proxima_fecha_cargada=m.proxima_fecha.isoformat()),
        )
        self.assertRedirects(respuesta, reverse("mantenciones:lista"))
        m.refresh_from_db()
        self.assertEqual(m.frecuencia_meses, 6)
        registro = RegistroAuditoria.objects.get()
        self.assertEqual(registro.accion, "modificar")
        self.assertEqual(registro.antes, {"frecuencia_meses": 12})
        self.assertEqual(registro.despues, {"frecuencia_meses": 6})

    def test_guardar_sin_cambios_no_deja_registro(self):
        m = crear_mantencion(self.e.condominio, dias=10)
        self.client.post(
            reverse("mantenciones:editar", args=[m.pk]),
            self.datos(nombre=m.nombre, frecuencia_meses=m.frecuencia_meses, proxima_fecha=m.proxima_fecha.isoformat(),
                       proveedor="", dias_anticipacion=m.dias_anticipacion,
                       proxima_fecha_cargada=m.proxima_fecha.isoformat()),
        )
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_formulario_de_edicion_viejo_no_pisa_la_fecha_de_una_ejecucion(self):
        """Pestaña vieja: se abre la edición, se registra una ejecución en otra y luego se envía la primera."""
        m = crear_mantencion(self.e.condominio, dias=-10, meses=6)  # vencida
        url = reverse("mantenciones:editar", args=[m.pk])
        abierto = self.client.get(url).context["form"]  # lo que ve la pestaña vieja
        enviado = {**self.datos(proxima_fecha=m.proxima_fecha.isoformat(), proveedor=""),
                   "proxima_fecha_cargada": abierto["proxima_fecha_cargada"].value().isoformat()}
        self.client.post(reverse("mantenciones:ejecucion", args=[m.pk]), {"fecha": timezone.localdate().isoformat()})
        m.refresh_from_db()
        recalculada = m.proxima_fecha
        self.assertGreater(recalculada, timezone.localdate())
        auditoria_antes = RegistroAuditoria.objects.count()

        respuesta = self.client.post(url, enviado)

        # Redirige (PRG): recargar un POST reenviaría la fecha vieja. El GET muestra la fecha recalculada.
        self.assertRedirects(respuesta, url, fetch_redirect_response=False)  # si no, consumiría el aviso
        seguida = self.client.get(url)
        self.assertContains(seguida, "Revisa los datos actuales")
        self.assertEqual(seguida.context["form"]["proxima_fecha_cargada"].value(), recalculada)
        m.refresh_from_db()
        self.assertEqual(m.proxima_fecha, recalculada)
        self.assertEqual(m.estado, Mantencion.Estado.AL_DIA)
        self.assertEqual(RegistroAuditoria.objects.count(), auditoria_antes)

    def test_editar_sin_la_fecha_cargada_se_rechaza(self):
        m = crear_mantencion(self.e.condominio, dias=10)
        respuesta = self.client.post(
            reverse("mantenciones:editar", args=[m.pk]),
            self.datos(proxima_fecha=m.proxima_fecha.isoformat(), nombre="Otro nombre"),
        )
        self.assertEqual(respuesta.status_code, 200)
        m.refresh_from_db()
        self.assertNotEqual(m.nombre, "Otro nombre")

    def test_editar_la_fecha_a_mano_con_el_formulario_al_dia_funciona(self):
        m = crear_mantencion(self.e.condominio, dias=10)
        respuesta = self.client.post(
            reverse("mantenciones:editar", args=[m.pk]),
            self.datos(proxima_fecha="2030-01-15", proveedor="", proxima_fecha_cargada=m.proxima_fecha.isoformat()),
        )
        self.assertRedirects(respuesta, reverse("mantenciones:lista"))
        m.refresh_from_db()
        self.assertEqual(m.proxima_fecha, date(2030, 1, 15))


class AdminSoloLecturaTest(TestCase):
    """El admin de Django no debe escribir mantenciones: se saltaría la validación y la auditoría de las vistas."""

    def setUp(self):
        self.e = crear_escenario()
        self.superusuario = get_user_model().objects.create_superuser("root@example.com", "changeme")
        self.client.force_login(self.superusuario)
        self.m = crear_mantencion(self.e.condominio)

    def test_ni_agregar_ni_editar_ni_borrar(self):
        ejecucion = EjecucionMantencion.objects.create(mantencion=self.m, fecha=timezone.localdate())
        for modelo, objeto in (("mantencion", self.m), ("ejecucionmantencion", ejecucion)):
            lista = reverse(f"admin:mantenciones_{modelo}_changelist")
            self.assertEqual(self.client.get(lista).status_code, 200, modelo)  # se puede mirar
            self.assertEqual(self.client.get(reverse(f"admin:mantenciones_{modelo}_add")).status_code, 403, modelo)
            self.assertEqual(self.client.post(reverse(f"admin:mantenciones_{modelo}_add"), {}).status_code, 403, modelo)
            cambiar = reverse(f"admin:mantenciones_{modelo}_change", args=[objeto.pk])
            self.assertEqual(self.client.post(cambiar, {}).status_code, 403, modelo)  # solo ver: sin guardar
            borrar = reverse(f"admin:mantenciones_{modelo}_delete", args=[objeto.pk])
            self.assertEqual(self.client.post(borrar, {"post": "yes"}).status_code, 403, modelo)
        self.assertEqual(EjecucionMantencion.objects.count(), 1)
        self.assertTrue(Mantencion.objects.filter(pk=self.m.pk).exists())

    def test_el_superusuario_no_puede_registrar_una_ejecucion_futura(self):
        manana = timezone.localdate() + timedelta(days=1)
        self.client.post(reverse("admin:mantenciones_ejecucionmantencion_add"),
                         {"mantencion": self.m.pk, "fecha": manana.isoformat()})
        self.assertFalse(EjecucionMantencion.objects.exists())


class ListaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.client.force_login(self.e.administrador)

    def test_orden_por_urgencia_vencidas_primero(self):
        crear_mantencion(self.e.condominio, "Al día", dias=60)
        crear_mantencion(self.e.condominio, "Por vencer", dias=5)
        crear_mantencion(self.e.condominio, "Vencida reciente", dias=-2)
        crear_mantencion(self.e.condominio, "Vencida antigua", dias=-20)
        respuesta = self.client.get(reverse("mantenciones:lista"))
        self.assertEqual([m.nombre for m in respuesta.context["mantenciones"]],
                         ["Vencida antigua", "Vencida reciente", "Por vencer", "Al día"])

    def test_insignias_y_chips_por_estado(self):
        crear_mantencion(self.e.condominio, "Al día", dias=60)
        crear_mantencion(self.e.condominio, "Por vencer", dias=5)
        crear_mantencion(self.e.condominio, "Vencida", dias=-2)
        respuesta = self.client.get(reverse("mantenciones:lista"))
        for clase, texto in (("al-dia", "Al día"), ("con-deuda", "Por vencer"), ("moroso", "Vencida")):
            self.assertContains(respuesta, f'<span class="insignia insignia-{clase}">{texto}</span>', html=True)
        cantidades = {chip["valor"]: chip["cantidad"] for chip in respuesta.context["chips"]}
        self.assertEqual(cantidades, {"": 3, "VENCIDA": 1, "POR_VENCER": 1, "AL_DIA": 1})

    def test_filtrar_por_estado_y_valor_desconocido(self):
        crear_mantencion(self.e.condominio, "Por vencer", dias=5)
        crear_mantencion(self.e.condominio, "Vencida", dias=-2)
        respuesta = self.client.get(reverse("mantenciones:lista"), {"estado": "VENCIDA"})
        self.assertEqual([m.nombre for m in respuesta.context["mantenciones"]], ["Vencida"])
        # Los chips siguen contando todo, para poder cambiar de filtro.
        self.assertEqual(respuesta.context["chips"][0]["cantidad"], 2)
        respuesta = self.client.get(reverse("mantenciones:lista"), {"estado": "NADA"})
        self.assertEqual(len(respuesta.context["mantenciones"]), 2)

    def test_lista_vacia(self):
        self.assertContains(self.client.get(reverse("mantenciones:lista")), "Aún no hay mantenciones registradas.")


class PermisosTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()
        self.m = crear_mantencion(self.e.condominio)
        self.rutas_de_escritura = [
            ("mantenciones:nueva", []), ("mantenciones:editar", [self.m.pk]), ("mantenciones:ejecucion", [self.m.pk]),
        ]

    def test_administrador_comite_y_conserje_ven_la_lista(self):
        for usuario, esperado in [(self.e.administrador, 200), (self.e.comite, 200), (self.e.conserje, 200),
                                  (self.e.residente, 403)]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("mantenciones:lista")).status_code, esperado, usuario)

    def test_solo_el_administrador_ve_los_botones_de_escritura(self):
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("mantenciones:lista")), reverse("mantenciones:nueva"))
        for usuario in (self.e.comite, self.e.conserje):
            self.client.force_login(usuario)
            respuesta = self.client.get(reverse("mantenciones:lista"))
            self.assertNotContains(respuesta, reverse("mantenciones:nueva"))
            self.assertNotContains(respuesta, reverse("mantenciones:editar", args=[self.m.pk]))

    def test_comite_conserje_y_residente_no_pueden_escribir(self):
        for usuario in (self.e.comite, self.e.conserje, self.e.residente):
            self.client.force_login(usuario)
            for nombre, args in self.rutas_de_escritura:
                url = reverse(nombre, args=args)
                self.assertEqual(self.client.get(url).status_code, 403, (usuario, nombre))
                self.assertEqual(self.client.post(url, {"nombre": "X"}).status_code, 403, (usuario, nombre))
        self.assertEqual(Mantencion.objects.count(), 1)
        self.assertFalse(EjecucionMantencion.objects.exists())
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_sin_sesion_va_al_login(self):
        respuesta = self.client.get(reverse("mantenciones:lista"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("iniciar-sesion", respuesta["Location"])


class AislamientoTest(TestCase):
    """Un administrador solo ve y toca lo de su condominio."""

    def setUp(self):
        self.e = crear_escenario()
        self.propia = crear_mantencion(self.e.condominio, "Propia")
        self.ajena = crear_mantencion(self.e.ajeno, "De otro condominio")
        self.client.force_login(self.e.administrador)

    def test_la_lista_no_muestra_las_de_otro_condominio(self):
        respuesta = self.client.get(reverse("mantenciones:lista"))
        self.assertContains(respuesta, "Propia")
        self.assertNotContains(respuesta, "De otro condominio")
        self.assertEqual(respuesta.context["chips"][0]["cantidad"], 1)

    def test_editar_y_registrar_ejecucion_de_otro_condominio_da_404(self):
        for nombre in ("mantenciones:editar", "mantenciones:ejecucion"):
            url = reverse(nombre, args=[self.ajena.pk])
            self.assertEqual(self.client.get(url).status_code, 404, nombre)
            self.assertEqual(self.client.post(url, {"nombre": "X", "fecha": "2026-01-01"}).status_code, 404, nombre)
        self.assertFalse(EjecucionMantencion.objects.exists())
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_el_condominio_no_se_puede_elegir_desde_el_formulario(self):
        self.client.post(reverse("mantenciones:nueva"), {
            "nombre": "Nueva", "frecuencia_meses": 3, "proxima_fecha": "2026-12-01", "dias_anticipacion": 15,
            "condominio": self.e.ajeno.pk,
        })
        self.assertEqual(Mantencion.objects.get(nombre="Nueva").condominio, self.e.condominio)


class DemoTest(TestCase):
    def test_deja_una_vencida_una_por_vencer_y_una_al_dia(self):
        e = crear_escenario()
        referencia = date(2026, 11, 16)
        ascensores = Proveedor.objects.create(
            condominio=e.condominio, rut="76.123.456-0", razon_social="Ascensores Sur SpA", rubro="Ascensores",
        )
        demo.cargar({"vista_verde": e.condominio, "proveedores": {"ascensores": ascensores},
                     "fecha_referencia_demo": referencia})
        estados = {m.nombre: (m.frecuencia_meses, m.estado_en(referencia)) for m in Mantencion.objects.all()}
        self.assertEqual(estados, {
            "Recarga de extintores": (12, Mantencion.Estado.POR_VENCER),
            "Revisión de red húmeda": (6, Mantencion.Estado.VENCIDA),
            "Mantención de ascensores": (1, Mantencion.Estado.AL_DIA),
        })
        self.assertEqual(Mantencion.objects.get(nombre="Mantención de ascensores").proveedor, ascensores)
        self.assertEqual(Condominio.objects.filter(mantenciones__isnull=False).distinct().count(), 1)
