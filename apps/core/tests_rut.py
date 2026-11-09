"""Pruebas del RUT con formato (Issue #77): funciones puras, campo, widget, filtro y aviso accesible."""
import importlib
from pathlib import Path

from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase

from apps.core.campos import RutField, RutInput
from apps.core.formato import calcular_dv, formatear_rut, normalizar_rut
from apps.core.formularios import FormularioBootstrap
from apps.core.templatetags.condohub import rut


class FormularioRut(FormularioBootstrap):
    rut = RutField(label="RUT", help_text="Ejemplo: 12.345.678-5")
    opcional = RutField(label="Otro RUT", required=False)
    nombre = forms.CharField(label="Nombre", help_text="Ayuda.")


def dibujar(plantilla, **contexto):
    return Template("{% load formularios condohub %}" + plantilla).render(Context(contexto))


class FormatearRutTest(SimpleTestCase):
    def test_formatea_con_puntos(self):
        casos = {
            "12345678-5": "12.345.678-5",
            "1234567-4": "1.234.567-4",
            "96511790-K": "96.511.790-K",
            "96511790-k": "96.511.790-K",
            "12.345.678-5": "12.345.678-5",
            " 12 345 678-5 ": "12.345.678-5",
            "01234567-4": "01.234.567-4",  # no pierde el cero inicial
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(formatear_rut(entrada), esperado)

    def test_lo_que_no_es_rut_queda_igual(self):
        for entrada in ["abc", "123456785", "", "123456-5", "123456789-5", "12345678-55", None, 123]:
            with self.subTest(entrada=entrada):
                self.assertEqual(formatear_rut(entrada), entrada)

    def test_no_comprueba_el_digito_verificador(self):
        self.assertEqual(formatear_rut("12345678-9"), "12.345.678-9")

    def test_el_digito_verificador_del_ejemplo_cuadra(self):
        self.assertEqual(calcular_dv("12345678"), "5")
        self.assertEqual(calcular_dv("1234567"), "4")

    def test_core_no_importa_cuentas_en_formato(self):
        fuente = Path(importlib.import_module("apps.core.formato").__file__).read_text(encoding="utf-8")
        importaciones = [linea for linea in fuente.splitlines() if linea.startswith(("import ", "from "))]
        self.assertFalse([linea for linea in importaciones if "cuentas" in linea])

    def test_imports_antiguos_desde_cuentas_siguen_funcionando(self):
        from apps.cuentas import validadores

        self.assertIs(validadores.normalizar_rut, normalizar_rut)
        self.assertIs(validadores.calcular_dv, calcular_dv)
        self.assertTrue(validadores.RUT_FORMATO.fullmatch("12345678-5"))
        self.assertEqual(validadores.normalizar_rut(" 12.345.678-k "), "12345678-K")


class FiltroRutTest(SimpleTestCase):
    def test_filtro(self):
        self.assertEqual(rut("12345678-5"), "12.345.678-5")
        self.assertEqual(rut("texto"), "texto")

    def test_none_y_vacio_dan_vacio_y_se_encadenan(self):
        self.assertEqual(rut(None), "")
        self.assertEqual(rut(""), "")
        self.assertEqual(dibujar('{{ v|rut|default:"—" }}', v=None), "—")
        self.assertEqual(dibujar('{{ v|rut|default:"—" }}', v="12345678-5"), "12.345.678-5")


class RutFieldTest(SimpleTestCase):
    def limpiar(self, valor, **kwargs):
        return RutField(**kwargs).clean(valor)

    def test_entradas_validas_salen_normalizadas(self):
        for entrada, esperado in {
            "12.345.678-5": "12345678-5", "12345678-5": "12345678-5", "1.234.567-4": "1234567-4",
            "10.000.013-k": "10000013-K", " 12.345.678-5 ": "12345678-5",
        }.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(self.limpiar(entrada), esperado)

    def test_mensajes_iguales_a_los_de_antes(self):
        with self.assertRaisesMessage(forms.ValidationError, "El dígito verificador del RUT no es correcto."):
            self.limpiar("12.345.678-9")
        for malo in ["abc", "123456785", "123456-5"]:
            with self.subTest(malo=malo), self.assertRaisesMessage(
                forms.ValidationError, "Formato de RUT inválido. Ejemplo: 12.345.678-5"
            ):
                self.limpiar(malo)

    def test_obligatorio_y_opcional(self):
        with self.assertRaises(forms.ValidationError):
            self.limpiar("")
        self.assertEqual(self.limpiar("", required=False), "")

    def test_largo_maximo(self):
        self.assertEqual(RutField().max_length, 12)

    def test_widget_muestra_puntos_y_deja_el_texto_invalido(self):
        widget = RutInput()
        self.assertEqual(widget.format_value("12345678-5"), "12.345.678-5")
        self.assertEqual(widget.format_value("12345678-9"), "12.345.678-9")
        self.assertEqual(widget.format_value("abc"), "abc")
        self.assertIsNone(widget.format_value(None))
        self.assertIsNone(widget.format_value(""))

    def test_placeholder_ficticio_es_valido(self):
        placeholder = RutInput().attrs["placeholder"]
        self.assertEqual(placeholder, "12.345.678-5")
        self.assertEqual(RutField().clean(placeholder), "12345678-5")

    def test_atributos_del_widget(self):
        html = dibujar("{{ campo|control }}", campo=FormularioRut()["rut"])
        for texto in ["data-rut", 'autocomplete="off"', 'spellcheck="false"', 'autocapitalize="characters"']:
            self.assertIn(texto, html)

    def test_formulario_que_vuelve_con_error_muestra_puntos(self):
        form = FormularioRut({"rut": "12345678-5", "nombre": ""})
        self.assertFalse(form.is_valid())
        self.assertIn('value="12.345.678-5"', dibujar("{{ campo|control }}", campo=form["rut"]))

    def test_formulario_con_rut_invalido_lo_muestra_tal_cual(self):
        form = FormularioRut({"rut": "12.345.678-9", "nombre": "x"})
        self.assertIn('value="12.345.678-9"', dibujar("{{ campo|control }}", campo=form["rut"]))


class AvisoVivoTest(SimpleTestCase):
    def test_region_aria_live_enlazada_con_ayuda_y_error(self):
        form = FormularioRut({"rut": "12.345.678-9", "nombre": "x"})
        html = dibujar('{% include "_campo.html" with campo=campo %}', campo=form["rut"])
        self.assertIn('id="id_rut_aviso" aria-live="polite"', html)
        self.assertIn('aria-describedby="id_rut_helptext id_rut_aviso id_rut_error"', html)
        self.assertLess(html.index('id="id_rut_aviso"'), html.index('id="id_rut_helptext"'))

    def test_orden_sin_error_y_sin_ayuda(self):
        form = FormularioRut()
        self.assertIn(
            'aria-describedby="id_rut_helptext id_rut_aviso"',
            dibujar("{{ campo|control }}", campo=form["rut"]),
        )
        self.assertIn('aria-describedby="id_opcional_aviso"', dibujar("{{ campo|control }}", campo=form["opcional"]))

    def test_campos_sin_aviso_vivo_salen_identicos(self):
        form = FormularioRut({"nombre": ""})
        html = dibujar('{% include "_campo.html" with campo=campo %}', campo=form["nombre"])
        self.assertNotIn("aviso", html)
        self.assertNotIn("aria-live", html)
        self.assertIn('aria-describedby="id_nombre_helptext id_nombre_error"', html)
