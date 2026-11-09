"""Pruebas del componente de campo accesible (contrato C6, Issue #75)."""
from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.formularios import FormularioBootstrap
from apps.core.pruebas import crear_escenario
from apps.proveedores.models import Proveedor


class FormularioEjemplo(FormularioBootstrap):
    nombre = forms.CharField(label="Nombre", help_text="Como figura en el contrato.")
    apellido = forms.CharField(label="Apellido", required=False)
    espacio = forms.ChoiceField(label="Espacio", choices=[("", "---------"), ("q", "Quincho")])
    propio = forms.ChoiceField(label="Propio", choices=[("", "Sin proveedor"), ("a", "A")], required=False)
    acepta = forms.BooleanField(label="Acepta", required=False)
    tipo = forms.ChoiceField(
        label="Tipo", choices=[("a", "Uno"), ("b", "Dos")], widget=forms.RadioSelect, help_text="Elija uno."
    )
    dias = forms.MultipleChoiceField(label="Días", choices=[("l", "Lunes")], widget=forms.CheckboxSelectMultiple, required=False)


def dibujar(plantilla, **contexto):
    return Template("{% load formularios %}" + plantilla).render(Context(contexto))


CONTROL = "{{ campo|control }}"
CAMPO = '{% include "_campo.html" with campo=campo %}'


class FiltroControlTest(SimpleTestCase):
    def test_campo_con_error_lleva_aria_invalid_y_describedby(self):
        form = FormularioEjemplo({"nombre": ""})
        html = dibujar(CONTROL, campo=form["nombre"])
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_nombre_helptext id_nombre_error"', html)
        self.assertIn("is-invalid", html)
        self.assertEqual(html.count("aria-describedby"), 1)
        self.assertEqual(html.count("aria-invalid"), 1)

    def test_campo_con_error_sin_ayuda_solo_enlaza_el_error(self):
        form = FormularioEjemplo({"espacio": ""})
        html = dibujar(CONTROL, campo=form["espacio"])
        self.assertIn('aria-describedby="id_espacio_error"', html)

    def test_campo_sin_error_no_lleva_aria_invalid(self):
        html = dibujar(CONTROL, campo=FormularioEjemplo()["nombre"])
        self.assertNotIn("aria-invalid", html)
        self.assertNotIn("is-invalid", html)
        self.assertIn('aria-describedby="id_nombre_helptext"', html)

    def test_campo_sin_error_ni_ayuda_no_lleva_describedby(self):
        html = dibujar(CONTROL, campo=FormularioEjemplo()["apellido"])
        self.assertNotIn("aria-describedby", html)

    def test_clase_segun_el_widget_sin_duplicar(self):
        form = FormularioEjemplo()
        self.assertIn('class="form-control"', dibujar(CONTROL, campo=form["nombre"]))
        self.assertIn('class="form-select"', dibujar(CONTROL, campo=form["espacio"]))
        self.assertIn('class="form-check-input"', dibujar(CONTROL, campo=form["acepta"]))
        html = dibujar(CONTROL, campo=form["tipo"])
        self.assertNotIn("form-control", html)
        self.assertIn("form-check-input", html)

    def test_es_casilla(self):
        form = FormularioEjemplo()
        self.assertEqual(dibujar("{{ campo|es_casilla }}", campo=form["acepta"]), "True")
        self.assertEqual(dibujar("{{ campo|es_casilla }}", campo=form["nombre"]), "False")
        self.assertEqual(dibujar("{{ campo|es_casilla }}", campo=form["dias"]), "False")


class RotularVaciosTest(SimpleTestCase):
    def test_select_sin_texto_propio_dice_seleccione(self):
        self.assertEqual(FormularioEjemplo().fields["espacio"].choices[0], ("", "Seleccione…"))

    def test_conserva_el_texto_propio(self):
        self.assertEqual(FormularioEjemplo().fields["propio"].choices[0], ("", "Sin proveedor"))

    def test_modelchoice_con_etiqueta_por_defecto_propia_y_none(self):
        class F(FormularioBootstrap):
            a = forms.ModelChoiceField(queryset=Proveedor.objects.none())
            b = forms.ModelChoiceField(queryset=Proveedor.objects.none(), empty_label="Todos los edificios")
            c = forms.ModelChoiceField(queryset=Proveedor.objects.none(), empty_label=None)

        form = F()
        self.assertEqual(form.fields["a"].empty_label, "Seleccione…")
        self.assertEqual(form.fields["b"].empty_label, "Todos los edificios")
        self.assertIsNone(form.fields["c"].empty_label)
        self.assertIn("Seleccione…", str(form["a"]))
        self.assertNotIn("---------", str(form["a"]))


class ComponenteCampoTest(SimpleTestCase):
    def test_error_enlaza_ayuda_y_error_en_el_html(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo({"nombre": ""})["nombre"])
        self.assertIn('aria-describedby="id_nombre_helptext id_nombre_error"', html)
        self.assertIn('id="id_nombre_helptext"', html)
        self.assertIn('id="id_nombre_error"', html)
        self.assertIn("invalid-feedback", html)

    def test_sin_error_no_hay_aria_invalid(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo()["nombre"])
        self.assertNotIn("aria-invalid", html)
        self.assertNotIn("invalid-feedback", html)

    def test_asterisco_oculto_a_lectores_de_pantalla_solo_en_obligatorios(self):
        form = FormularioEjemplo()
        self.assertIn('<span class="text-danger" aria-hidden="true">*</span>', dibujar(CAMPO, campo=form["nombre"]))
        self.assertNotIn("*", dibujar(CAMPO, campo=form["apellido"]))

    def test_prefijo_dibuja_input_group(self):
        html = dibujar('{% include "_campo.html" with campo=campo prefijo="$" %}', campo=FormularioEjemplo()["nombre"])
        self.assertIn("input-group", html)
        self.assertIn("data-prefijo>$<", html)

    def test_casilla_usa_form_check(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo()["acepta"])
        self.assertIn('class="form-check"', html)
        self.assertIn("form-check-label", html)

    def test_radio_va_en_fieldset_con_legend(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo({})["tipo"])
        self.assertIn("<fieldset", html)
        self.assertIn("<legend", html)
        self.assertIn('aria-describedby="id_tipo_helptext id_tipo_error"', html)
        self.assertEqual(html.count('type="radio"'), 2)

    def test_varios_errores_quedan_dentro_del_elemento_enlazado(self):
        form = FormularioEjemplo({"nombre": "x"})
        form.add_error("nombre", "Primer error.")
        form.add_error("nombre", "Segundo error.")
        html = dibujar(CAMPO, campo=form["nombre"])
        self.assertEqual(html.count('id="id_nombre_error"'), 1)
        self.assertNotIn("id_nombre_error_2", html)
        elemento = html.split('id="id_nombre_error"')[1].split("</div></div>")[0]
        self.assertIn("Primer error.", elemento)
        self.assertIn("Segundo error.", elemento)

    def test_radio_obligatorio_conserva_required(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo()["tipo"])
        self.assertEqual(html.count(" required"), 2)

    def test_grupo_de_casillas_va_en_fieldset(self):
        html = dibujar(CAMPO, campo=FormularioEjemplo()["dias"])
        self.assertIn("<fieldset", html)
        self.assertIn('type="checkbox"', html)


class PaginasConFormularioTest(TestCase):
    """Las páginas que usan _formulario.html responden 200 con su rol, y 403 con uno no permitido."""

    SOLO_ADMIN = [
        "comunicados:nuevo", "condominios:edificio_nuevo", "condominios:unidad_nueva", "condominios:importar",
        "cuentas:usuario_nuevo", "gastos:periodo_nuevo", "proveedores:nuevo", "reservas:espacio_nuevo",
    ]
    TODOS = ["cuentas:perfil", "cuentas:cambiar_clave"]
    SOLO_RESIDENTE = ["incidentes:nuevo", "reservas:nueva", "privacidad:solicitud_nueva"]

    def setUp(self):
        self.e = crear_escenario()

    def test_administrador_ve_las_paginas_con_el_componente(self):
        self.client.force_login(self.e.administrador)
        self.comprobar_paginas(self.SOLO_ADMIN + self.TODOS)

    def comprobar_paginas(self, nombres):
        for nombre in nombres:
            with self.subTest(nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'class="form-')
                self.assertNotContains(respuesta, "---------")
                self.assertNotContains(respuesta, "aria-invalid")

    def test_residente_sigue_sin_permiso_donde_no_le_corresponde(self):
        self.client.force_login(self.e.residente)
        for nombre in self.SOLO_ADMIN:
            with self.subTest(nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 403)
                self.assertContains(respuesta, "No tienes permisos", status_code=403)
        self.comprobar_paginas(self.TODOS + self.SOLO_RESIDENTE)

    def test_formulario_con_error_marca_el_campo(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("proveedores:nuevo"), {"rut": "", "razon_social": ""})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'aria-invalid="true"')
        self.assertContains(respuesta, 'aria-describedby="id_razon_social_helptext id_razon_social_error"')
        self.assertContains(respuesta, "invalid-feedback")

    def test_post_sin_javascript_guarda_igual(self):
        self.client.force_login(self.e.administrador)
        respuesta = self.client.post(reverse("proveedores:nuevo"), {
            "rut": "76.086.428-5", "razon_social": "Aseo Ltda.", "rubro": "Aseo",
            "contacto": "Ana", "telefono": "+56912345678", "correo": "aseo@prueba.cl",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Proveedor.objects.filter(condominio=self.e.condominio, razon_social="Aseo Ltda.").exists())

    def test_reporte_de_morosidad_responde_200(self):
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(reverse("gastos:reporte")).status_code, 200)
