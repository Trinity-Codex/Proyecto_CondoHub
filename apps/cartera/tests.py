"""
Pruebas de cartera: acceso de administrador general, su admin y la auditoría (Issue #54, RF18 y RF20).

Datos ficticios de `crear_escenario()` (condominios «Prueba» y «Ajeno») más un administrador general
`gerente` creado en cada prueba. Las pruebas de la página, el reporte y las descargas siguen más abajo.
"""
from datetime import date
from decimal import Decimal

from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.auditoria.servicios import Accion
from apps.condominios.models import Condominio, Edificio, Residente, Unidad
from apps.core.pruebas import crear_escenario, crear_usuario
from apps.cuentas.demo import CLAVE_DEMO
from apps.cuentas.models import Usuario
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.gastos.reportes import generar_reporte

from .consolidado import armar_cartera, meses_disponibles
from .models import AsignacionCartera
from .permisos import condominios_de_cartera

RUT_GERENTE = "12.345.678-5"
PAGADO = DetalleGastoComun.Estado.PAGADO
PENDIENTE = DetalleGastoComun.Estado.PENDIENTE


class CarteraBase(TestCase):
    """Escenario común: un administrador general ficticio y un superusuario, sin asignaciones todavía."""

    def setUp(self):
        self.e = crear_escenario()
        self.gerente = crear_usuario("gerente@prueba.cl", rut=RUT_GERENTE)
        self.super = crear_usuario("super@prueba.cl", is_staff=True, is_superuser=True)

    def asignar(self, *condominios, usuario=None):
        for condominio in condominios:
            AsignacionCartera.objects.create(usuario=usuario or self.gerente, condominio=condominio)


class AsignacionTest(CarteraBase):
    def test_el_par_repetido_se_rechaza(self):
        self.asignar(self.e.condominio)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.asignar(self.e.condominio)


class CondominiosDeCarteraTest(CarteraBase):
    def test_devuelve_solo_los_asignados(self):
        self.asignar(self.e.condominio)
        self.assertEqual(list(condominios_de_cartera(self.gerente)), [self.e.condominio])

    def test_no_incluye_condominios_inactivos(self):
        self.asignar(self.e.condominio, self.e.ajeno)
        Condominio.objects.filter(pk=self.e.ajeno.pk).update(activo=False)
        self.assertEqual(list(condominios_de_cartera(self.gerente)), [self.e.condominio])

    def test_el_superusuario_ve_todos_los_activos(self):
        Condominio.objects.filter(pk=self.e.ajeno.pk).update(activo=False)
        self.assertEqual(list(condominios_de_cartera(self.super)), [self.e.condominio])

    def test_quien_no_tiene_asignaciones_no_ve_ninguno(self):
        # Ni siquiera el administrador del condominio: la membresía no da acceso a la cartera.
        for usuario in (self.gerente, self.e.administrador, self.e.comite, self.e.conserje, self.e.residente):
            with self.subTest(usuario=usuario.email):
                self.assertFalse(condominios_de_cartera(usuario).exists())

    def test_una_persona_con_dos_asignaciones_no_repite_condominios(self):
        self.asignar(self.e.condominio, self.e.ajeno)
        self.assertEqual(condominios_de_cartera(self.gerente).count(), 2)


class AdminCarteraTest(CarteraBase):
    """Escenario «Acceso por rol» de `condominios`: solo el superusuario asigna o quita el acceso."""

    def test_solo_el_superusuario_entra(self):
        staff = crear_usuario("staff@prueba.cl", is_staff=True)
        self.asignar(self.e.condominio)
        asignacion = AsignacionCartera.objects.get()
        urls = [
            reverse("admin:cartera_asignacioncartera_changelist"),
            reverse("admin:cartera_asignacioncartera_add"),
            reverse("admin:cartera_asignacioncartera_delete", args=[asignacion.pk]),
        ]
        # staff sin superusuario: el panel lo deja entrar, pero no a esta sección (403).
        # El resto no es staff: el panel lo lleva a su inicio de sesión (302).
        casos = [
            (staff, 403), (self.e.administrador, 302), (self.e.comite, 302), (self.e.conserje, 302),
            (self.e.residente, 302), (self.gerente, 302), (self.super, 200),
        ]
        for usuario, esperado in casos:
            self.client.force_login(usuario)
            for url in urls:
                with self.subTest(usuario=usuario.email, url=url):
                    self.assertEqual(self.client.get(url).status_code, esperado)

    def test_el_formulario_avisa_que_el_borrado_en_cascada_no_se_audita(self):
        self.client.force_login(self.super)
        pagina = self.client.get(reverse("admin:cartera_asignacioncartera_add"))
        self.assertContains(pagina, "NO queda en el registro de auditoría")

    def test_la_asignacion_se_ve_en_solo_lectura(self):
        """Sin edición: al abrirla no hay botón de guardar ni se acepta un POST."""
        self.asignar(self.e.condominio)
        asignacion = AsignacionCartera.objects.get()
        self.client.force_login(self.super)
        url = reverse("admin:cartera_asignacioncartera_change", args=[asignacion.pk])
        self.assertNotContains(self.client.get(url), 'name="_save"')
        respuesta = self.client.post(url, {"usuario": self.gerente.pk, "condominio": self.e.ajeno.pk})
        self.assertEqual(respuesta.status_code, 403)
        asignacion.refresh_from_db()
        self.assertEqual(asignacion.condominio, self.e.condominio)


class AuditoriaAdminTest(CarteraBase):
    """Asignar y quitar el acceso deja un registro por condominio, con el id de la persona y sin sus datos."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.super)

    def registros(self, condominio):
        return RegistroAuditoria.objects.filter(condominio_id=condominio.pk, accion=Accion.CAMBIAR_ROL)

    def asignar_por_admin(self, condominio):
        return self.client.post(
            reverse("admin:cartera_asignacioncartera_add"), {"usuario": self.gerente.pk, "condominio": condominio.pk}
        )

    def test_asignar_registra_el_cambio_de_rol(self):
        respuesta = self.asignar_por_admin(self.e.condominio)
        self.assertEqual(respuesta.status_code, 302)
        asignacion = AsignacionCartera.objects.get()
        registro = self.registros(self.e.condominio).get()
        self.assertEqual(registro.usuario_id, self.super.pk)
        self.assertEqual((registro.objeto_tipo, registro.objeto_id), ("asignacioncartera", str(asignacion.pk)))
        self.assertEqual(registro.antes, {"administrador_general": None})
        self.assertEqual(registro.despues, {"administrador_general": self.gerente.pk})
        # Solo el id de la persona: ni su nombre ni su RUT (con y sin puntos) quedan en el registro.
        guardado = f"{registro.antes}{registro.despues}"
        for dato in (self.gerente.first_name, self.gerente.email, RUT_GERENTE, RUT_GERENTE.replace(".", "")):
            self.assertNotIn(dato, guardado)
        self.assertFalse(self.registros(self.e.ajeno).exists())  # el otro condominio no recibe nada

    def test_quitar_registra_el_cambio_de_rol(self):
        self.asignar_por_admin(self.e.condominio)
        asignacion = AsignacionCartera.objects.get()
        respuesta = self.client.post(
            reverse("admin:cartera_asignacioncartera_delete", args=[asignacion.pk]), {"post": "yes"}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(AsignacionCartera.objects.exists())
        quitar = self.registros(self.e.condominio).first()  # el más reciente
        self.assertEqual(quitar.antes, {"administrador_general": self.gerente.pk})
        self.assertEqual(quitar.despues, {"administrador_general": None})
        self.assertEqual(quitar.usuario_id, self.super.pk)
        self.assertEqual(self.registros(self.e.condominio).count(), 2)  # el alta y la baja

    def test_el_borrado_en_lote_registra_un_evento_por_condominio(self):
        self.asignar(self.e.condominio, self.e.ajeno)
        respuesta = self.client.post(
            reverse("admin:cartera_asignacioncartera_changelist"),
            {
                "action": "delete_selected", "post": "yes",
                "_selected_action": list(AsignacionCartera.objects.values_list("pk", flat=True)),
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(AsignacionCartera.objects.exists())
        for condominio in (self.e.condominio, self.e.ajeno):
            with self.subTest(condominio=condominio.nombre):
                registro = self.registros(condominio).get()
                self.assertEqual(registro.antes, {"administrador_general": self.gerente.pk})
                self.assertEqual(registro.despues, {"administrador_general": None})

    def test_si_la_asignacion_falla_no_queda_registro(self):
        self.asignar(self.e.condominio)
        # El par ya existe: el formulario lo rechaza y no se guarda ningún evento.
        self.asignar_por_admin(self.e.condominio)
        self.assertEqual(AsignacionCartera.objects.count(), 1)
        self.assertFalse(self.registros(self.e.condominio).exists())


# --------------------------------------------------------------------------
# La página de cartera, el reporte desde ella y las descargas (tareas 4.x)
# --------------------------------------------------------------------------
def emitir(condominio, anio, mes, cobros):
    """Período EMITIDO con un cobro por (unidad, estado); cada cobro de $42.000 (40.000 + 2.000 de fondo)."""
    periodo = PeriodoGasto.objects.create(condominio=condominio, anio=anio, mes=mes, estado=PeriodoGasto.Estado.EMITIDO)
    for unidad, estado in cobros:
        DetalleGastoComun.objects.create(
            periodo=periodo, unidad=unidad, monto=40000, monto_fondo_reserva=2000, estado=estado
        )
    return periodo


class EscenarioCartera(CarteraBase):
    """
    «Prueba» (Torre A y B) con agosto, septiembre y octubre emitidos, como en el reporte de morosidad;
    «Ajeno» con solo octubre; «Tercero» (nunca asignado) con octubre. El gerente tiene Prueba y Ajeno.
    """

    def setUp(self):
        super().setUp()
        e = self.e
        self.tercero = Condominio.objects.create(nombre="Tercero", direccion="Calle 3", comuna="Maipú")
        torre = Edificio.objects.create(condominio=self.tercero, nombre="Torre T")
        self.unidad_tercero = Unidad.objects.create(edificio=torre, numero="T1", alicuota=Decimal("1"))
        unidades = (e.a101, e.a102, e.b101)
        self.ago = emitir(e.condominio, 2026, 8, zip(unidades, (PAGADO, PENDIENTE, PAGADO)))
        self.sep = emitir(e.condominio, 2026, 9, zip(unidades, (PAGADO, PENDIENTE, PENDIENTE)))
        self.oct = emitir(e.condominio, 2026, 10, zip(unidades, (PENDIENTE, PENDIENTE, PENDIENTE)))
        self.oct_ajeno = emitir(e.ajeno, 2026, 10, [(e.unidad_ajena, PAGADO)])
        self.oct_tercero = emitir(self.tercero, 2026, 10, [(self.unidad_tercero, PENDIENTE)])
        self.asignar(e.condominio, e.ajeno)
        self.url = reverse("cartera:inicio")

    def abrir(self, usuario=None, url=None, **parametros):
        self.client.force_login(usuario or self.gerente)
        return self.client.get(url or self.url, parametros)

    def filas_csv(self, respuesta):
        """El CSV como lista de filas (listas de textos)."""
        texto = respuesta.content.decode("utf-8")
        self.assertTrue(texto.startswith("﻿"))
        return [linea.split(";") for linea in texto.lstrip("﻿").splitlines()]


class ConsolidadoTest(EscenarioCartera):
    def test_cada_fila_cuadra_con_el_reporte_del_condominio(self):
        """Escenario «Cifras iguales al reporte de cada condominio»: fila, generar_reporte y la página del reporte."""
        cartera = armar_cartera(condominios_de_cartera(self.gerente), 2026, 10)
        self.assertEqual([f.condominio for f in cartera.filas], [self.e.ajeno, self.e.condominio])
        for fila in cartera.filas:
            reporte = generar_reporte(fila.periodo)
            with self.subTest(condominio=fila.condominio.nombre):
                self.assertEqual(
                    (fila.emitido, fila.recaudado, fila.porcentaje_recaudacion, fila.deuda_anterior),
                    (reporte.total_emitido, reporte.total_recaudado, reporte.porcentaje_recaudacion,
                     reporte.deuda_anterior),
                )
                self.assertEqual(fila.unidades_morosas, len(reporte.unidades_morosas))
        # Prueba en octubre (todo impago): emitido 126.000, deuda anterior de agosto y septiembre.
        prueba = next(f for f in cartera.filas if f.condominio == self.e.condominio)
        self.assertEqual((prueba.emitido, prueba.recaudado, prueba.porcentaje_recaudacion), (126000, 0, 0))
        self.assertEqual((prueba.deuda_anterior, prueba.unidades_morosas), (42000 + 84000, 2))

    def test_la_fila_cuadra_con_la_pagina_del_reporte(self):
        self.client.force_login(self.e.administrador)
        pagina = self.client.get(reverse("gastos:reporte"), {"periodo": self.sep.pk})
        reporte = pagina.context["reporte"]
        fila = armar_cartera(condominios_de_cartera(self.gerente), 2026, 9).filas[1]
        self.assertEqual(fila.condominio, self.e.condominio)
        self.assertEqual(
            (fila.emitido, fila.recaudado, fila.porcentaje_recaudacion, fila.deuda_anterior, fila.unidades_morosas),
            (reporte.total_emitido, reporte.total_recaudado, reporte.porcentaje_recaudacion,
             reporte.deuda_anterior, len(reporte.unidades_morosas)),
        )

    def test_los_totales_suman_las_filas_y_el_porcentaje_sale_de_los_totales(self):
        cartera = armar_cartera(condominios_de_cartera(self.gerente), 2026, 10)
        self.assertEqual(cartera.total_emitido, 126000 + 42000)
        self.assertEqual(cartera.total_recaudado, 42000)  # solo Ajeno pagó
        self.assertEqual(cartera.deuda_anterior, 126000)
        self.assertEqual(cartera.unidades_morosas, 2)
        self.assertEqual(cartera.porcentaje_recaudacion, round(42000 * 100 / 168000, 1))  # 25,0: no el promedio de 0 y 100

    def test_condominio_sin_periodo_emitido_en_el_mes(self):
        cartera = armar_cartera(condominios_de_cartera(self.gerente), 2026, 9)
        ajeno = next(f for f in cartera.filas if f.condominio == self.e.ajeno)
        self.assertFalse(ajeno.tiene_periodo)
        self.assertEqual((ajeno.emitido, ajeno.recaudado, ajeno.deuda_anterior, ajeno.unidades_morosas), (0, 0, 0, 0))
        self.assertEqual(cartera.total_emitido, 126000)  # solo Prueba suma
        pagina = self.abrir(mes="2026-09")
        self.assertContains(pagina, "Sin período emitido")

    def test_un_mes_sin_periodos_da_porcentaje_cero_decimal(self):
        cartera = armar_cartera(condominios_de_cartera(self.gerente), 2026, 11)
        self.assertEqual((cartera.total_emitido, cartera.porcentaje_recaudacion), (0, 0.0))
        self.assertIsInstance(cartera.porcentaje_recaudacion, float)

    def test_un_periodo_abierto_no_cuenta(self):
        PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=11)  # ABIERTO
        self.assertNotIn((2026, 11), meses_disponibles(condominios_de_cartera(self.gerente)))


class CarteraViewTest(EscenarioCartera):
    def test_muestra_una_fila_por_condominio_con_sus_cifras_y_enlaces(self):
        pagina = self.abrir(mes="2026-10")
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, "Prueba")
        self.assertContains(pagina, "Ajeno")
        self.assertContains(pagina, "$126.000")  # emitido de Prueba en octubre
        enlace = reverse("cartera:reporte", args=[self.e.condominio.pk]) + f"?periodo={self.oct.pk}"
        self.assertContains(pagina, enlace)
        self.assertContains(pagina, "insignia-moroso")  # Prueba tiene morosas
        self.assertContains(pagina, "insignia-al-dia")  # Ajeno no

    def test_mes_por_defecto_y_mes_invalido(self):
        """Sin ?mes=, o con uno mal escrito o sin períodos, se muestra el más reciente; sin error."""
        for parametros in ({}, {"mes": "2026-9"}, {"mes": "octubre"}, {"mes": "2020-01"}, {"mes": "2026-11"}):
            with self.subTest(parametros=parametros):
                pagina = self.abrir(**parametros)
                self.assertEqual(pagina.status_code, 200)
                self.assertEqual(pagina.context["clave_mes"], "2026-10")

    def test_el_mes_pedido_se_respeta_y_el_selector_ofrece_solo_meses_con_periodos(self):
        pagina = self.abrir(mes="2026-09")
        self.assertEqual(pagina.context["clave_mes"], "2026-09")
        self.assertEqual([c for c, _ in pagina.context["form"].fields["mes"].choices], ["2026-10", "2026-09", "2026-08"])

    def test_sin_periodos_emitidos_la_pagina_lo_indica(self):
        vacio = Condominio.objects.create(nombre="Vacío", direccion="Calle 4", comuna="Lo Prado")
        otro = crear_usuario("otro@prueba.cl")
        self.asignar(vacio, usuario=otro)
        pagina = self.abrir(otro, mes="2026-10")
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, "Todavía no hay períodos emitidos")
        self.assertIsNone(pagina.context["cartera"])
        # Y su CSV no revienta: vuelve a la cartera con un aviso.
        self.assertRedirects(self.client.get(reverse("cartera:csv")), self.url)

    def test_solo_los_condominios_asignados(self):
        inactivo = Condominio.objects.create(nombre="Inactivo", direccion="Calle 5", comuna="Pudahuel", activo=False)
        self.asignar(inactivo)
        for url in (self.url, reverse("cartera:csv")):
            with self.subTest(url=url):
                respuesta = self.abrir(url=url, mes="2026-10")
                contenido = respuesta.content.decode("utf-8")
                self.assertIn("Prueba", contenido)
                self.assertIn("Ajeno", contenido)
                self.assertNotIn("Tercero", contenido)
                self.assertNotIn("Inactivo", contenido)

    def test_el_superusuario_ve_todos_los_condominios_activos(self):
        pagina = self.abrir(self.super, mes="2026-10")
        self.assertEqual(pagina.status_code, 200)
        for nombre in ("Prueba", "Ajeno", "Tercero"):
            self.assertContains(pagina, nombre)

    def test_acceso_por_rol(self):
        """Administrador, comité, conserje y residente sin asignación reciben 403; sin sesión, al inicio de sesión."""
        urls = [
            self.url,
            reverse("cartera:csv"),
            reverse("cartera:reporte", args=[self.e.condominio.pk]),
            reverse("cartera:reporte_csv", args=[self.e.condominio.pk]),
        ]
        e = self.e
        for url in urls:
            for usuario in (e.administrador, e.comite, e.conserje, e.residente):
                with self.subTest(url=url, usuario=usuario.email):
                    self.assertEqual(self.abrir(usuario, url=url).status_code, 403)
            with self.subTest(url=url, usuario="sin sesión"):
                self.client.logout()
                self.assertRedirects(
                    self.client.get(url), reverse("cuentas:iniciar_sesion") + "?next=" + url,
                    fetch_redirect_response=False,
                )


class CarteraCsvTest(EscenarioCartera):
    def test_una_fila_por_condominio_y_la_de_totales(self):
        respuesta = self.abrir(url=reverse("cartera:csv"), mes="2026-10")
        self.assertEqual(respuesta["Content-Disposition"], 'attachment; filename="cartera-2026-10.csv"')
        filas = self.filas_csv(respuesta)
        self.assertEqual(filas[0][0], "Condominio")
        self.assertEqual([f[0] for f in filas[1:]], ["Ajeno", "Prueba", "Total"])
        self.assertEqual(filas[2], ["Prueba", "Octubre 2026", "126000", "0", "0,0", "126000", "2"])
        self.assertEqual(filas[3], ["Total", "Octubre 2026", "168000", "42000", "25,0", "126000", "2"])

    def test_el_porcentaje_usa_coma_decimal(self):
        # Septiembre: Prueba recauda 42.000 de 126.000 = 33,3 %.
        filas = self.filas_csv(self.abrir(url=reverse("cartera:csv"), mes="2026-09"))
        self.assertEqual(filas[2][4], "33,3")

    def test_un_condominio_sin_periodo_sale_con_su_aviso(self):
        filas = self.filas_csv(self.abrir(url=reverse("cartera:csv"), mes="2026-09"))
        self.assertEqual(filas[1], ["Ajeno", "Sin período emitido", "", "", "", "", ""])

    def test_el_nombre_de_un_condominio_no_se_evalua_como_formula(self):
        """Escenario «Descarga en CSV segura»."""
        Condominio.objects.filter(pk=self.e.ajeno.pk).update(nombre="=SUMA(1)")
        filas = self.filas_csv(self.abrir(url=reverse("cartera:csv"), mes="2026-10"))
        self.assertIn("'=SUMA(1)", [f[0] for f in filas])
        self.assertNotIn("=SUMA(1)", [f[0] for f in filas])


class ReporteDesdeCarteraTest(EscenarioCartera):
    def setUp(self):
        super().setUp()
        self.url_reporte = reverse("cartera:reporte", args=[self.e.condominio.pk])
        self.url_csv = reverse("cartera:reporte_csv", args=[self.e.condominio.pk])

    def test_muestra_el_reporte_del_condominio_con_las_cifras_de_la_fila(self):
        pagina = self.abrir(url=self.url_reporte, periodo=self.oct.pk)
        self.assertEqual(pagina.status_code, 200)
        reporte = pagina.context["reporte"]
        fila = armar_cartera(condominios_de_cartera(self.gerente), 2026, 10).filas[1]
        self.assertEqual(reporte.periodo, self.oct)
        self.assertEqual(
            (reporte.total_emitido, reporte.total_recaudado, reporte.deuda_anterior, len(reporte.unidades_morosas)),
            (fila.emitido, fila.recaudado, fila.deuda_anterior, fila.unidades_morosas),
        )
        # Modo consulta: migas que vuelven a la cartera de ese mes y CSV propio.
        self.assertContains(pagina, reverse("cartera:inicio") + "?mes=2026-10")
        self.assertContains(pagina, self.url_csv)
        self.assertNotContains(pagina, reverse("gastos:periodos"))

    def test_sin_periodo_en_la_url_muestra_el_ultimo_emitido(self):
        self.assertEqual(self.abrir(url=self.url_reporte).context["reporte"].periodo, self.oct)

    def test_el_csv_es_el_del_reporte(self):
        respuesta = self.abrir(url=self.url_csv, periodo=self.sep.pk)
        self.assertEqual(respuesta["Content-Disposition"], 'attachment; filename="morosidad-2026-09.csv"')
        filas = self.filas_csv(respuesta)
        self.assertEqual(filas[0][0], "Edificio")
        self.assertEqual(filas[-1][3], "126000")  # la fila de totales: emitido

    def test_el_csv_sin_periodo_valido_vuelve_al_reporte_de_la_cartera(self):
        respuesta = self.abrir(url=self.url_csv, periodo=99999)
        self.assertRedirects(respuesta, f"{self.url_reporte}?periodo=99999", fetch_redirect_response=False)

    def test_un_condominio_no_asignado_da_404_en_la_pagina_y_en_el_csv(self):
        for nombre in ("cartera:reporte", "cartera:reporte_csv"):
            url = reverse(nombre, args=[self.tercero.pk])
            with self.subTest(url=url):
                self.assertEqual(self.abrir(url=url, periodo=self.oct_tercero.pk).status_code, 404)

    def test_un_condominio_inactivo_asignado_da_404(self):
        Condominio.objects.filter(pk=self.e.ajeno.pk).update(activo=False)
        self.assertEqual(self.abrir(url=reverse("cartera:reporte", args=[self.e.ajeno.pk])).status_code, 404)

    def test_un_periodo_de_otro_condominio_no_se_muestra(self):
        """Pedir por URL el período de Tercero en el reporte de Prueba: el formulario lo rechaza."""
        pagina = self.abrir(url=self.url_reporte, periodo=self.oct_tercero.pk)
        self.assertIsNone(pagina.context["reporte"])
        self.assertNotContains(pagina, "Tercero")

    def test_no_cambia_el_condominio_activo(self):
        """El administrador de Prueba que además es administrador general de Ajeno sigue en Prueba."""
        usuario = self.e.administrador
        self.asignar(self.e.ajeno, usuario=usuario)
        self.client.force_login(usuario)
        antes = self.client.get(reverse("core:inicio")).context["condominio_activo"]
        reporte = self.client.get(reverse("cartera:reporte", args=[self.e.ajeno.pk]))
        self.assertEqual(reporte.status_code, 200)
        self.assertEqual(reporte.context["reporte"].periodo, self.oct_ajeno)
        self.assertEqual(reporte.context["condominio_activo"], self.e.condominio)  # el de su sesión, no Ajeno
        despues = self.client.get(reverse("core:inicio")).context["condominio_activo"]
        self.assertEqual((antes, despues), (self.e.condominio, self.e.condominio))

    def test_el_reporte_de_gastos_comunes_sigue_igual(self):
        """El administrador entra a su reporte como siempre; el gerente (sin rol en el condominio) no."""
        self.client.force_login(self.e.administrador)
        self.assertContains(self.client.get(reverse("gastos:reporte")), reverse("gastos:periodos"))
        self.client.force_login(self.gerente)
        self.assertRedirects(self.client.get(reverse("gastos:reporte")), reverse("core:sin_condominio"),
                             fetch_redirect_response=False)


class SinDatosPersonalesTest(EscenarioCartera):
    """Escenario «Sin datos personales»: ni nombre ni RUT de una residente ficticia en ninguna salida."""

    NOMBRE, APELLIDO, RUT = "Zulema", "Quispe", "18.765.432-1"

    def setUp(self):
        super().setUp()
        residente = crear_usuario("zulema@prueba.cl", rut=self.RUT)
        Usuario.objects.filter(pk=residente.pk).update(first_name=self.NOMBRE, last_name=self.APELLIDO)
        Residente.objects.create(usuario=residente, unidad=self.e.a102, desde=date(2020, 1, 1))

    def test_ninguna_pagina_ni_csv_la_nombra(self):
        urls = [
            (reverse("cartera:inicio"), {"mes": "2026-10"}),
            (reverse("cartera:csv"), {"mes": "2026-10"}),
            (reverse("cartera:reporte", args=[self.e.condominio.pk]), {"periodo": self.sep.pk}),
            (reverse("cartera:reporte_csv", args=[self.e.condominio.pk]), {"periodo": self.sep.pk}),
        ]
        prohibidos = (self.NOMBRE, self.APELLIDO, self.RUT, self.RUT.replace(".", ""), "18765432")
        for url, parametros in urls:
            contenido = self.abrir(url=url, **parametros).content.decode("utf-8")
            for dato in prohibidos:
                with self.subTest(url=url, dato=dato):
                    self.assertNotIn(dato, contenido)
        # La unidad morosa sí está (A102): el reporte sigue mostrando cifras por unidad, solo sin personas.
        self.assertContains(self.abrir(url=urls[2][0], periodo=self.sep.pk), "A102")


# --------------------------------------------------------------------------
# Menú y entrada (tareas 5.x)
# --------------------------------------------------------------------------
class MenuYEntradaTest(EscenarioCartera):
    def test_el_enlace_aparece_solo_para_quien_tiene_cartera(self):
        enlace = f'href="{reverse("cartera:inicio")}"'
        casos = [
            (self.gerente, True), (self.super, True), (self.e.administrador, False), (self.e.comite, False),
            (self.e.conserje, False), (self.e.residente, False),
        ]
        for usuario, lo_ve in casos:
            self.client.force_login(usuario)
            pagina = self.client.get(reverse("core:inicio"), follow=True)
            with self.subTest(usuario=usuario.email):
                if lo_ve:
                    self.assertContains(pagina, enlace)
                else:
                    self.assertNotContains(pagina, enlace)

    def test_el_enlace_no_esta_dentro_de_administracion(self):
        """Un administrador que también es administrador general lo ve como enlace propio, no en el desplegable."""
        self.asignar(self.e.ajeno, usuario=self.e.administrador)
        self.client.force_login(self.e.administrador)
        pagina = self.client.get(reverse("core:inicio"))
        self.assertContains(pagina, f'class="nav-link " href="{reverse("cartera:inicio")}"')
        self.assertNotContains(pagina, f'class="dropdown-item " href="{reverse("cartera:inicio")}"')

    def test_la_cartera_marca_su_enlace(self):
        pagina = self.abrir()
        self.assertContains(pagina, f'class="nav-link active" href="{reverse("cartera:inicio")}"')

    def test_el_gerente_sin_membresia_solo_ve_su_cartera_en_el_menu(self):
        pagina = self.abrir()
        self.assertNotContains(pagina, "Administración")
        self.assertNotContains(pagina, reverse("comunicados:lista"))


class SinRolEnElCondominioTest(EscenarioCartera):
    """Escenario «Sin rol dentro del condominio»: el administrador general sin membresía termina en la cartera."""

    def test_las_paginas_del_condominio_lo_llevan_a_la_cartera(self):
        self.client.force_login(self.gerente)
        paginas = ["core:inicio", "condominios:unidades", "gastos:periodos", "pagos:cobranza", "core:sin_condominio"]
        for nombre in paginas:
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre), follow=True)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.redirect_chain[-1][0], reverse("cartera:inicio"))

    def test_no_tiene_condominio_activo_ni_opciones_en_el_selector(self):
        pagina = self.abrir()
        self.assertIsNone(pagina.context["condominio_activo"])
        self.assertFalse(pagina.context["mis_condominios"])
        self.assertNotContains(pagina, "cambiar-condominio")  # ninguna acción del selector de condominios

    def test_quien_no_tiene_nada_sigue_viendo_la_pagina_sin_condominio(self):
        sin_nada = crear_usuario("nadie@prueba.cl")
        self.client.force_login(sin_nada)
        respuesta = self.client.get(reverse("core:inicio"), follow=True)
        self.assertTemplateUsed(respuesta, "core/sin_condominio.html")


# --------------------------------------------------------------------------
# Datos demo (tarea 6.1)
# --------------------------------------------------------------------------
class DemoCarteraTest(TestCase):
    """`cargar_demo` deja al administrador general con los dos condominios y la cartera con cifras."""

    def cargar(self, *argumentos):
        call_command("cargar_demo", *argumentos, stdout=StringIO())

    def test_la_cartera_demo_tiene_dos_filas_con_cifras(self):
        self.cargar()
        gerencia = Usuario.objects.get(email="gerencia@condohub.cl")
        self.assertTrue(gerencia.check_password(CLAVE_DEMO))
        self.assertFalse(gerencia.membresias.exists())  # sin rol en ningún condominio: solo consulta
        self.client.force_login(gerencia)
        pagina = self.client.get(reverse("cartera:inicio"))
        filas = pagina.context["cartera"].filas
        self.assertEqual([f.condominio.nombre for f in filas], ["Condominio Vista Verde", "Edificio Los Aromos"])
        for fila in filas:
            with self.subTest(condominio=fila.condominio.nombre):
                self.assertTrue(fila.tiene_periodo)
                self.assertGreater(fila.emitido, 0)
        vista_verde = filas[0]
        self.assertGreater(vista_verde.recaudado, 0)
        self.assertGreater(vista_verde.unidades_morosas, 0)

    def test_la_asignacion_queda_en_la_auditoria_con_el_sistema_como_autor(self):
        self.cargar()
        registros = RegistroAuditoria.objects.filter(accion=Accion.CAMBIAR_ROL)
        self.assertEqual(registros.count(), 2)
        self.assertEqual({r.usuario_nombre for r in registros}, {"Sistema"})

    def test_reiniciar_dos_veces_no_falla_ni_duplica(self):
        self.cargar()
        self.cargar("--reiniciar")
        self.cargar("--reiniciar")
        self.assertEqual(AsignacionCartera.objects.count(), 2)
        self.assertEqual(Usuario.objects.filter(email="gerencia@condohub.cl").count(), 1)
