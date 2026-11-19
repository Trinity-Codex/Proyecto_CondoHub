"""
Pruebas de la proyección anual de gastos comunes (RQ-06, #121).

Escenario ficticio (crear_escenario: A101 0,4 y A102 0,3 en Torre A; B101 0,3 en Torre B), año base 2026:
  - agosto: período emitido con egresos de $100.000
  - octubre: período emitido con egresos de $200.000 y una multa (ítem de cobro) de $25.000 a A101,
    que NO entra en la base
  - noviembre: período ABIERTO con $999.999 de egresos, que tampoco cuenta
  - el condominio "Ajeno" emite agosto con $777.000: nunca debe aparecer
Promedio de los meses reales: (100.000 + 200.000) / 2 = $150.000 para los otros diez meses.
"""
import csv
import io
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import RegistroAuditoria
from apps.core.pruebas import crear_escenario

from .models import Egreso, ItemCobro, PeriodoGasto
from .proyeccion import porcentaje_texto, proyectar, reajustar
from .servicios import emitir_periodo, guardar_item

URL = reverse("gastos:proyeccion")
URL_CSV = reverse("gastos:proyeccion_csv")


def agregar_egreso(periodo, monto, usuario):
    Egreso.objects.create(periodo=periodo, categoria=Egreso.Categoria.ASEO, descripcion="Aseo ficticio",
                          monto=monto, fecha=date(periodo.anio, periodo.mes, 5), creado_por=usuario)


def periodo_emitido(condominio, usuario, mes, egresos, items=()):
    periodo = PeriodoGasto.objects.create(condominio=condominio, anio=2026, mes=mes)
    agregar_egreso(periodo, egresos, usuario)
    for item, unidades in items:
        guardar_item(ItemCobro(periodo=periodo, creado_por=usuario, **item), unidades, usuario=usuario)
    emitir_periodo(periodo, usuario=usuario)
    return periodo


class EscenarioProyeccionMixin:
    def setUp(self):
        self.e = e = crear_escenario()
        periodo_emitido(e.condominio, e.administrador, 8, 100000)
        multa = {"nombre": "Multa ficticia", "modo": ItemCobro.Modo.POR_UNIDAD, "monto": 25000,
                 "alcance": ItemCobro.Alcance.ALGUNAS}
        periodo_emitido(e.condominio, e.administrador, 10, 200000, items=[(multa, [e.a101])])
        noviembre = PeriodoGasto.objects.create(condominio=e.condominio, anio=2026, mes=11)
        agregar_egreso(noviembre, 999999, e.administrador)
        periodo_emitido(e.ajeno, e.administrador, 8, 777000)

    def proyectar(self, ipc="0", crecimiento="0"):
        return proyectar(self.e.condominio, 2026, Decimal(ipc), Decimal(crecimiento))


class CalculoProyeccionTest(EscenarioProyeccionMixin, TestCase):
    def test_base_con_meses_reales_y_promedio(self):
        p = self.proyectar()
        self.assertEqual(p.meses_reales, 2)
        bases = {m.mes: (m.base, m.estimado) for m in p.meses}
        self.assertEqual(bases[8], (100000, False))
        self.assertEqual(bases[10], (200000, False))  # sin la multa de $25.000
        self.assertEqual(bases[11], (150000, True))  # el período abierto no cuenta
        self.assertEqual(len(p.meses_estimados), 10)
        self.assertEqual(p.total_base, 300000 + 10 * 150000)

    def test_cambio_proporcional_con_cifras_sencillas(self):
        agosto = {(ipc, c): self.proyectar(ipc, c).meses[7] for ipc, c in [("0", "0"), ("10", "0"), ("10", "10")]}
        self.assertEqual([m.egresos for m in agosto.values()], [100000, 110000, 121000])
        self.assertEqual([m.fondo for m in agosto.values()], [5000, 5500, 6050])  # 5 % vigente
        # Por alícuota: A101 (0,4) paga 44.000 de los 110.000.
        self.assertEqual(agosto[("10", "0")].por_unidad[0], (44000, 2200))
        self.assertEqual(reajustar(100000, Decimal("-10"), Decimal("0")), 90000)

    def test_porcentajes_en_texto(self):
        casos = {"4.50": "4,5 %", "10": "10 %", "-2": "−2 %", "-0": "0 %", "0.00": "0 %"}
        for valor, texto in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(porcentaje_texto(Decimal(valor)), texto)

    def test_total_de_cada_mes_cuadra_con_las_unidades(self):
        # IPC y crecimiento con decimales: los montos no se reparten exacto entre las unidades.
        p = self.proyectar("3.33", "1.1")
        self.assertEqual(p.meses[7].egresos, 104467)  # 100.000 × 1,0333 × 1,011 = 104.466,63
        for mes in p.meses:
            with self.subTest(mes=mes.mes):
                self.assertEqual(sum(e + f for e, f in mes.por_unidad), mes.total)
        self.assertEqual(sum(f["total"] for f in p.filas_unidades), p.total)

    def test_partes_iguales_y_fondo_del_periodo_vigente(self):
        # El período más reciente (diciembre, abierto) fija el criterio y el % del fondo.
        PeriodoGasto.objects.create(condominio=self.e.condominio, anio=2026, mes=12, porcentaje_fondo_reserva=10,
                                    criterio_prorrateo=PeriodoGasto.Criterio.PARTES_IGUALES,
                                    referencia_reglamento="Art. ficticio 1")
        agosto = self.proyectar("10", "0").meses[7]
        self.assertEqual(agosto.fondo, 11000)
        # 110.000 / 3 = 36.666,67: el peso que sobra va a una sola unidad.
        self.assertEqual(sorted(e for e, _ in agosto.por_unidad), [36666, 36667, 36667])
        self.assertEqual(sum(e + f for e, f in agosto.por_unidad), agosto.total)

    def test_reproducible(self):
        def huella(p):
            return [(m.base, m.egresos, m.fondo, m.por_unidad) for m in p.meses], p.supuestos
        self.assertEqual(huella(self.proyectar("4.5", "2")), huella(self.proyectar("4.5", "2")))

    def test_sin_meses_reales_no_inventa(self):
        p = proyectar(self.e.condominio, 2025, Decimal("4"), Decimal("0"))
        self.assertEqual(p.meses, [])
        self.assertEqual(p.total, 0)

    def test_aislamiento_entre_condominios(self):
        p = self.proyectar()
        self.assertEqual([u.numero for u in p.unidades], ["A101", "A102", "B101"])
        self.assertNotIn(777000, [m.base for m in p.meses])
        ajena = proyectar(self.e.ajeno, 2026, Decimal("0"), Decimal("0"))
        self.assertEqual(ajena.meses[7].base, 777000)
        self.assertEqual(ajena.meses_reales, 1)


class VistaProyeccionTest(EscenarioProyeccionMixin, TestCase):
    def test_administrador_y_comite(self):
        for usuario in (self.e.administrador, self.e.comite):
            self.client.force_login(usuario)
            for url in (URL, URL_CSV):
                with self.subTest(usuario=usuario.email, url=url):
                    self.assertEqual(self.client.get(url, {"anio": 2026}).status_code, 200)

    def test_residente_y_conserje_reciben_403(self):
        for usuario in (self.e.residente, self.e.conserje):
            self.client.force_login(usuario)
            for url in (URL, URL_CSV):
                with self.subTest(usuario=usuario.email, url=url):
                    self.assertEqual(self.client.get(url, {"anio": 2026}).status_code, 403)

    def test_pantalla_muestra_supuestos_y_estimados(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(URL, {"anio": 2026, "ipc": "4,5", "crecimiento": "2"})
        self.assertContains(respuesta, "Supuestos usados")
        self.assertContains(respuesta, "4,5 %")
        self.assertContains(respuesta, "estimado")
        self.assertNotContains(respuesta, "Torre única")  # unidades del otro condominio

    def test_sin_anio_usa_el_anio_en_curso(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.get(URL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["form"].cleaned_data["ipc"], 0)

    def test_parametros_invalidos_sin_error_500(self):
        self.client.force_login(self.e.administrador)
        invalidos = [{"ipc": "abc"}, {"ipc": "NaN"}, {"ipc": "Infinity"}, {"ipc": "31"}, {"ipc": "-10.5"},
                     {"crecimiento": "51"}, {"crecimiento": "1e9"}, {"ipc": "1,234"}, {"anio": "x"},
                     {"anio": "1999"}, {"anio": "2100"}]
        for parametros in invalidos:
            with self.subTest(parametros=parametros):
                consulta = {"anio": 2026, **parametros}
                respuesta = self.client.get(URL, consulta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIsNone(respuesta.context["proyeccion"])
                self.assertTrue(respuesta.context["form"].errors)
                self.assertRedirects(self.client.get(URL_CSV, consulta), f"{URL}?{respuesta.context['consulta']}",
                                     fetch_redirect_response=False)

    def test_csv_sin_meses_reales_redirige(self):
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(URL_CSV, {"anio": 2025}).status_code, 302)
        self.assertContains(self.client.get(URL, {"anio": 2025}), "no tiene períodos emitidos")

    def test_csv_igual_a_la_pantalla(self):
        self.client.force_login(self.e.administrador)
        # Crecimiento negativo: el CSV no debe anteponerle un apóstrofo (celda_segura).
        consulta = {"anio": 2026, "ipc": "3,33", "crecimiento": "-1.1"}
        p = self.client.get(URL, consulta).context["proyeccion"]
        texto = self.client.get(URL_CSV, consulta).content.decode("utf-8-sig")
        filas = list(csv.reader(io.StringIO(texto), delimiter=";"))[1:]

        esperado = []
        for mes in p.meses:
            nombre = f"{mes.nombre} 2027"
            esperado += [[nombre, u.edificio.nombre, u.numero, "", "", str(e), str(f), str(e + f)]
                         for u, (e, f) in zip(p.unidades, mes.por_unidad)]
            esperado.append([nombre, "Total del mes", "", str(mes.base), "Sí" if mes.estimado else "No",
                             str(mes.egresos), str(mes.fondo), str(mes.total)])
        esperado += [["Total 2027", f["unidad"].edificio.nombre, f["unidad"].numero, "", "", str(f["egresos"]),
                      str(f["fondo"]), str(f["total"])] for f in p.filas_unidades]
        esperado.append(["Total 2027", "Total del año", "", str(p.total_base), "", str(p.total_egresos),
                         str(p.total_fondo), str(p.total)])
        esperado.append([])
        esperado += [[t, v] for t, v in p.supuestos]
        self.assertEqual(filas, esperado)

    def test_solo_lectura_sin_auditoria(self):
        self.client.force_login(self.e.administrador)
        antes = RegistroAuditoria.objects.count()
        self.client.get(URL, {"anio": 2026})
        self.client.get(URL_CSV, {"anio": 2026})
        self.assertEqual(RegistroAuditoria.objects.count(), antes)
