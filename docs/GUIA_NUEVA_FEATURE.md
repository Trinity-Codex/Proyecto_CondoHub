# Guía: cómo agregar un módulo nuevo a CondoHub

Receta paso a paso para construir una funcionalidad completa (modelo → formulario → vistas →
rutas → plantillas → menú → pruebas) siguiendo el mismo patrón que los módulos que ya existen.
El módulo de referencia es **`apps/comunicados`**: cuando tengas dudas, mira cómo está hecho ahí.

Como ejemplo construiremos un **registro de mascotas**: cada residente registra las mascotas de su
unidad y el administrador ve todas las del condominio. (Es solo un ejemplo para aprender; no está
en el backlog.)

> Antes de empezar: toma tu Issue en el tablero y crea tu rama (ver [CONTRIBUTING.md](../CONTRIBUTING.md)).

---

## Paso 1. Crear la app

Con el entorno virtual activado, desde la carpeta del proyecto:

```bash
mkdir apps\mascotas
python manage.py startapp mascotas apps\mascotas
```

Abre `apps/mascotas/apps.py` y cambia `name` para que incluya la carpeta `apps.`:

```python
class MascotasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mascotas"            # <- con "apps." delante
    verbose_name = "Mascotas"
```

Regístrala en `config/settings.py`, dentro de `INSTALLED_APPS`:

```python
    "apps.mascotas",        # registro de mascotas por unidad
```

## Paso 2. El modelo

`apps/mascotas/models.py`:

```python
from django.conf import settings
from django.db import models


class Mascota(models.Model):
    class Especie(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"
        OTRA = "OTRA", "Otra"

    # REGLA MULTI-CONDOMINIO: todo registro debe saber a qué condominio pertenece.
    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="mascotas")
    unidad = models.ForeignKey("condominios.Unidad", on_delete=models.CASCADE, related_name="mascotas")
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    especie = models.CharField(max_length=10, choices=Especie.choices)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["unidad", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.unidad})"
```

Crea la migración y aplícala:

```bash
python manage.py makemigrations mascotas
python manage.py migrate
```

> Si el modelo no tiene un campo `condominio` directo, debe poder llegar a él (ej. `Reserva →
> espacio → condominio`). Eso se usa en el Paso 4 con `campo_condominio`.

## Paso 3. El formulario

`apps/mascotas/forms.py`:

```python
from apps.condominios.models import Unidad
from apps.core.formularios import ModeloFormularioBootstrap   # agrega el estilo Bootstrap solo

from .models import Mascota


class MascotaForm(ModeloFormularioBootstrap):
    class Meta:
        model = Mascota
        fields = ["unidad", "nombre", "especie"]   # solo lo que llena el usuario

    def __init__(self, *args, usuario, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        # SEGURIDAD: la lista de unidades muestra solo las del usuario en el condominio activo.
        self.fields["unidad"].queryset = Unidad.objects.filter(
            edificio__condominio=condominio, residentes__usuario=usuario, residentes__activo=True
        )
```

## Paso 4. Las vistas (y los permisos)

Cada vista combina **tres piezas**, siempre en este orden:

1. `RolRequeridoMixin` → **quién** puede entrar (`roles_permitidos`; `None` = cualquier miembro).
2. `CondominioQuerysetMixin` → **solo registros del condominio activo** (nunca de otro).
3. La vista genérica de Django → **qué hace** (`ListView`, `CreateView`, `UpdateView`, `DeleteView`, `DetailView`).

`apps/mascotas/views.py`:

```python
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.core.permisos import ADMINISTRADOR, RESIDENTE, CondominioQuerysetMixin, RolRequeridoMixin, tiene_rol

from .forms import MascotaForm
from .models import Mascota


class MascotaListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    model = Mascota
    template_name = "mascotas/lista.html"
    context_object_name = "mascotas"

    def get_queryset(self):
        qs = super().get_queryset()            # ya viene filtrado por el condominio activo
        if tiene_rol(self.request, ADMINISTRADOR):
            return qs                          # el administrador ve todas
        return qs.filter(registrada_por=self.request.user)   # el residente, solo las suyas


class MascotaCreateView(RolRequeridoMixin, CreateView):
    roles_permitidos = [RESIDENTE]
    model = Mascota
    form_class = MascotaForm
    template_name = "mascotas/formulario.html"
    success_url = reverse_lazy("mascotas:lista")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user           # el formulario los necesita (Paso 3)
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def form_valid(self, form):
        # Lo que el usuario NO llena lo completa la vista (nunca desde el formulario).
        form.instance.condominio = self.request.condominio
        form.instance.registrada_por = self.request.user
        messages.success(self.request, "Mascota registrada.")
        return super().form_valid(form)
```

Variables útiles en cualquier vista (las pone `apps/core/middleware.py`):

| Variable | Qué es |
|---|---|
| `request.condominio` | Condominio que el usuario está viendo |
| `request.roles` | Roles del usuario en ese condominio, ej. `{"RESIDENTE", "COMITE"}` |
| `tiene_rol(request, ADMINISTRADOR, COMITE)` | `True` si tiene alguno de esos roles |

### Vistas que no son de un solo condominio: la cartera (`apps/cartera/permisos.py`)

El administrador general (Issue #54) no tiene condominio activo ni rol en ninguno: el superusuario le asigna
condominios desde `/admin/` (modelo `AsignacionCartera`) y solo los consulta. Por eso sus vistas **no** usan
`RolRequeridoMixin` ni `CondominioQuerysetMixin`; usan estas dos piezas:

```python
from apps.cartera.permisos import CarteraRequeridaMixin, condominios_de_cartera

condominios_de_cartera(request.user)   # condominios activos asignados; el superusuario, todos los activos


class MiVistaDeCartera(CarteraRequeridaMixin, TemplateView):   # sin sesión: login; sin cartera: 403
    def get_context_data(self, **kwargs):
        condominio = get_object_or_404(self.condominios, pk=self.kwargs["pk"])  # no asignado: 404
```

Toda consulta de una vista así parte de `condominios_de_cartera(...)`. El reporte de recaudación se puede abrir
para un condominio dado sin cambiar el activo: `ReporteBase` en `apps/gastos/views.py` toma el condominio de
`get_condominio_reporte()`, y la cartera lo reemplaza (ver `apps/cartera/views.py`).

### Descargar una tabla en CSV (`apps/core/exportar.py`)

```python
from apps.core.exportar import respuesta_csv

return respuesta_csv("morosidad-2026-10.csv", ["Unidad", "Saldo"], [[unidad.numero, saldo] for ...])
```

Devuelve el archivo para Excel (separador «;», UTF-8 con BOM) y pasa cada celda por `celda_segura`, que antepone
un apóstrofo a los textos que empiezan con `=`, `+`, `-`, `@`, tabulación o retorno de carro. No armes un CSV a mano.

### Filtros, chips y búsqueda en un listado (`apps/core/listados.py`)

`FiltrosGetMixin` lee los filtros por GET (`?estado=...`), arma los chips con su cantidad (`_chips.html`) y deja
en el contexto `filtros_url`, `hay_filtros` y `url_limpiar`. Si además el listado acepta búsqueda (`?q=`),
declara `busqueda = True`: `self.texto_busqueda()` devuelve el texto normalizado (sin espacios sobrantes,
hasta 100 caracteres y 5 palabras) y «Limpiar filtros» aparece también con `q`. Qué columnas se buscan lo
decide tu app, siempre sobre el queryset ya acotado por condominio y rol (nunca `Modelo.objects.all()`).
El ejemplo real es Unidades (`apps/condominios/views.py` y `apps/condominios/busqueda.py`):

```python
class UnidadesView(FiltrosGetMixin, UnidadesAccesoMixin, CondominioQuerysetMixin, ListView):
    parametros_filtro = {"ocupacion": list(OCUPACIONES)}
    busqueda = True

    def _buscar(self, unidades):
        return filtrar_unidades(unidades, self.texto_busqueda(), ver_rut=ver_rut(self.request))
```

Para sugerencias mientras se escribe, `static/js/busqueda.js` (ya cargado en `base.html`) se activa solo en un
`<input type="search" name="q" data-busqueda="{% url '...' %}">` dentro de un `<form method="get">` que tenga
una región `<div class="visually-hidden" aria-live="polite" data-busqueda-estado></div>`. El endpoint
responde `{"resultados": [{"edificio", "unidad", "residentes": [{"nombre", "rut"?}]}], "hay_mas"}`: si lo
reutilizas en otro listado, adapta el JS a tus campos y entrega en el JSON solo lo que tu listado ya muestra a
ese rol. Mira `condominios/unidades.html` y `SugerenciasUnidadesView`.

## Paso 5. Las rutas

`apps/mascotas/urls.py`:

```python
from django.urls import path

from . import views

app_name = "mascotas"   # permite usar {% url 'mascotas:lista' %}

urlpatterns = [
    path("", views.MascotaListView.as_view(), name="lista"),
    path("nueva/", views.MascotaCreateView.as_view(), name="nueva"),
]
```

Y en `config/urls.py`, antes de la línea de `apps.core.urls`:

```python
    path("mascotas/", include("apps.mascotas.urls")),
```

## Paso 6. Las plantillas

Van en `apps/mascotas/templates/mascotas/`. Siempre extienden `base.html`.

`lista.html`:

```django
{% extends "base.html" %}
{% block titulo %}Mascotas{% endblock %}

{% block contenido %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h1 class="h3 mb-0"><i class="bi bi-heart"></i> Mascotas</h1>
  {% if es_residente %}
  <a class="btn btn-primary" href="{% url 'mascotas:nueva' %}"><i class="bi bi-plus-lg"></i> Registrar</a>
  {% endif %}
</div>
<ul class="list-group">
  {% for m in mascotas %}
  <li class="list-group-item">{{ m.nombre }} · {{ m.get_especie_display }} · {{ m.unidad }}</li>
  {% empty %}
  <li class="list-group-item text-muted">No hay mascotas registradas.</li>
  {% endfor %}
</ul>
{% endblock %}
```

`formulario.html` (el include dibuja todos los campos con sus errores):

```django
{% extends "base.html" %}
{% block titulo %}Registrar mascota{% endblock %}

{% block contenido %}
<div class="row justify-content-center"><div class="col-lg-6">
  <h1 class="h3 mb-3">Registrar mascota</h1>
  <div class="card"><div class="card-body">
    <form method="post" novalidate>
      {% csrf_token %}
      {% include "_formulario.html" with form=form %}
      <button class="btn btn-primary" type="submit">Guardar</button>
      <a class="btn btn-outline-secondary" href="{% url 'mascotas:lista' %}">Cancelar</a>
    </form>
  </div></div>
</div></div>
{% endblock %}
```

En las plantillas tienes disponibles: `es_admin`, `es_comite`, `es_residente`, `es_conserje`,
`condominio_activo` y `user` (vienen de `apps/core/context_processors.py`).
Íconos: https://icons.getbootstrap.com/ · Componentes: https://getbootstrap.com/docs/5.3/

### Campos accesibles (contrato C6)

`{% include "_formulario.html" with form=form %}` dibuja cada campo con `templates/_campo.html`: etiqueta, control,
ayuda y errores enlazados con `aria-describedby` y `aria-invalid`, asterisco `aria-hidden` en los obligatorios y
placeholder con contraste AA. Si necesitas una grilla o un prefijo, incluye el campo suelto:

```django
<div class="col-md-6">{% include "_campo.html" with campo=form.monto prefijo="$" %}</div>
```

**Montos en pesos (#76):** para un campo de dinero usa `MontoField` (`apps/core/campos.py`): acepta «$ 1.250.000», «1.250.000» y «1250000»,
rechaza decimales y puntos mal agrupados, y `_campo.html` le pone el prefijo «$» solo. En un `forms.Form`:
`monto = MontoField(label="Monto", min_value=1)`; en un `ModelForm`, `field_classes = {"monto": MontoField}` en el `Meta`
(se conservan los validadores del modelo y no pongas un `NumberInput` en `widgets`). El JS `static/js/formato.js` agrega los puntos
mientras se escribe y nunca cambia un monto que no sea válido. Para mostrar dinero usa `{{ valor|pesos }}`.

**RUT (#77):** para un campo de RUT usa `RutField` (`apps/core/campos.py`): acepta con o sin puntos y «k» minúscula, valida igual que
`validar_rut` y `cleaned_data` sale normalizado (`12345678-5`). En un `forms.Form`: `rut = RutField(label="RUT")`; en un `ModelForm`,
`field_classes = {"rut": RutField}` en el `Meta`. `_campo.html` agrega solo la región `aria-live` del aviso y el JS da formato en vivo.
Para mostrar un RUT usa `{{ valor|rut }}` (`{% load condohub %}`); `{{ valor|rut|default:"—" }}` si puede faltar. Las funciones puras
(`normalizar_rut`, `calcular_dv`, `formatear_rut`) viven en `apps/core/formato.py`; `apps.cuentas.validadores` las sigue exportando.

Los `RadioSelect` y `CheckboxSelectMultiple` salen en un `fieldset` con `legend` (`_opciones.html`, lo elige `_campo.html`).
Los filtros `control` y `es_casilla` están en `{% load formularios %}`. Las listas desplegables muestran «Seleccione…»
(lo hace `BootstrapMixin`; tu `empty_label` propio se respeta).

## Paso 7. El enlace en el menú

En `templates/base.html`, dentro de `<ul class="navbar-nav me-auto">`:

```django
<li class="nav-item"><a class="nav-link {% if seccion == 'mascotas' %}active{% endif %}" href="{% url 'mascotas:lista' %}"><i class="bi bi-heart"></i> Mascotas</a></li>
```

## Paso 8 (opcional). Notificar con el patrón Observer

Si tu módulo debe avisar a alguien (ej. "Llegó tu encomienda"):

1. Haz que tu modelo herede de `Sujeto`: `class Encomienda(Sujeto, models.Model)`.
2. En el método que corresponda, llama a `self.notificar(Evento(condominio=..., titulo=..., mensaje=..., destinatarios=[...], url=...))`.
3. Suscribe el observador en `apps/notificaciones/apps.py`: `Encomienda.suscribir(notificador)`.

Ejemplos completos: `Comunicado.publicar()` e `Incidente.cambiar_estado()`.

## Paso 9. Las pruebas

`apps/mascotas/tests.py`. `crear_escenario()` crea un condominio con un usuario por rol, unidades
y un segundo condominio "ajeno":

```python
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario

from .models import Mascota


class MascotaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def test_residente_registra_mascota(self):
        self.client.force_login(self.e.residente)
        self.client.post(reverse("mascotas:nueva"), {"unidad": self.e.a101.pk, "nombre": "Toby", "especie": "PERRO"})
        self.assertEqual(Mascota.objects.get().condominio, self.e.condominio)

    def test_no_puede_usar_una_unidad_ajena(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("mascotas:nueva"), {"unidad": self.e.b101.pk, "nombre": "Toby", "especie": "PERRO"})
        self.assertIn("unidad", respuesta.context["form"].errors)

    def test_conserje_no_puede_registrar(self):
        self.client.force_login(self.e.conserje)
        self.assertEqual(self.client.get(reverse("mascotas:nueva")).status_code, 403)
```

```bash
python manage.py test apps
```

Prueba siempre: **lo que debe funcionar**, **lo que un rol no debe poder hacer** (403/404) y que
**no se vean datos de otro condominio**.

## Paso 10. Los datos demo de tu app

Desde el Issue #62 cada app tiene sus datos demo en `apps/<app>/demo.py`, con una función
`cargar(datos)`. `python manage.py cargar_demo` las llama en orden (lista `APPS_DEMO` de
`apps/core/management/commands/cargar_demo.py`) dentro de una transacción: **no edites ese
archivo**, edita solo el `demo.py` de tu app.

`datos` es un diccionario que las apps anteriores ya llenaron:

| Clave | Qué es | Lo deja |
|---|---|---|
| `usuarios` | `{"administrador": Usuario, "comite": ..., "residente": ...}` | `cuentas` |
| `vista_verde`, `los_aromos` | Los dos condominios demo | `condominios` |
| `unidades` | Unidades de Vista Verde por "Torre-número": `datos["unidades"]["A-101"]` | `condominios` |
| `proveedores` | `{"ascensores": Proveedor, "aseo": ..., "seguridad": ...}` | `proveedores` |
| `periodos` | `{"hace_dos_meses": ..., "anterior": ..., "actual": PeriodoGasto}` | `gastos` |

```python
# apps/mascotas/demo.py
from apps.mascotas.models import Mascota


def cargar(datos):
    Mascota.objects.create(
        condominio=datos["vista_verde"], unidad=datos["unidades"]["A-101"], nombre="Toby", especie="PERRO"
    )
```

Si tu app deja algo que otra necesita, agrégalo a `datos` con una clave nueva y anótala en el
comentario de tu `demo.py`. `cargar_demo --reiniciar` borra los dos condominios (y en cascada lo que
cuelga de ellos), así que un modelo con `condominio` se limpia solo.

La prueba `CargarDemoTest` de `apps/core/tests.py` compara una "huella" (conteos y sumas) de la demo.
Si agregas datos demo a propósito, actualiza el número que corresponde en `HUELLA`.

## Paso 11 (si tu módulo entrega un documento). PDF con `renderizar_pdf`

`apps/core/pdf.py` (contrato C0) convierte una plantilla de Django en PDF con xhtml2pdf:

```python
from apps.core.pdf import renderizar_pdf


class AvisoCobroPdfView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    model = DetalleGastoComun
    campo_condominio = "periodo__condominio"

    def get(self, request, *args, **kwargs):
        cobro = self.get_object()
        return renderizar_pdf("pagos/pdf/aviso.html", {"cobro": cobro}, f"aviso-{cobro.pk}")
```

- `renderizar_pdf(plantilla, contexto, nombre)` devuelve un `HttpResponse` (`application/pdf`,
  se abre en el navegador). El `.pdf` del nombre se agrega solo y se limpian caracteres como `/`.
- `generar_pdf(plantilla, contexto)` devuelve los bytes, para las pruebas o para adjuntar a un correo.
- Si la conversión falla, lanza `ErrorPDF`: nunca entrega un PDF a medias.
- La plantilla se renderiza **sin `request`**: pasa en el contexto todo lo que usa.

La plantilla extiende `core/pdf/base.html` (logo, márgenes y pie con la fecha y el número de página):

```django
{% extends "core/pdf/base.html" %}
{% load condohub %}
{% block titulo %}Aviso de cobro{% endblock %}
{% block encabezado %}Aviso de cobro {{ cobro.periodo }}{% endblock %}
{% block contenido %}
<table>
  <tr><th scope="col">Concepto</th><th scope="col" class="derecha">Monto</th></tr>
  <tr><td>Gastos comunes</td><td class="derecha">{{ cobro.monto|pesos }}</td></tr>
</table>
{% endblock %}
```

**CSS que admite xhtml2pdf:** CSS 2 básico (márgenes, bordes, colores, fuentes, tamaños,
`text-align`, `@page` para el tamaño de hoja). **No admite** flexbox, grid, variables CSS ni
Bootstrap: las columnas se maquetan con `<table>` (solo en el PDF; en las páginas web, nunca).
Las imágenes se leen **solo de `static/`** con `{% static %}`; una URL externa se ignora.

Para probarlo, lee el texto del PDF con `pypdf` (ya viene instalado):

```python
from io import BytesIO
from pypdf import PdfReader

texto = PdfReader(BytesIO(respuesta.content)).pages[0].extract_text()
self.assertIn("$1.234.567", texto)
```

---

## Lista de revisión antes de abrir el Pull Request

- [ ] La app está en `INSTALLED_APPS` y su `apps.py` dice `name = "apps.<app>"`.
- [ ] El modelo tiene `condominio` (o llega a él) y la migración está creada y subida.
- [ ] Cada vista tiene `RolRequeridoMixin` y, si lista/edita registros, `CondominioQuerysetMixin`.
- [ ] Los formularios limitan las listas desplegables al condominio activo y al usuario.
- [ ] Lo que el usuario no debe elegir (condominio, autor...) lo completa la vista en `form_valid`.
- [ ] Las plantillas extienden `base.html` y se ven bien en el celular.
- [ ] Hay pruebas y `python manage.py test apps` pasa completo.
- [ ] Si la funcionalidad se ve en la demo, sus datos están en el `demo.py` de tu app.
- [ ] El código está comentado para que un compañero lo entienda.
