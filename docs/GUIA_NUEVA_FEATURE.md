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

---

## Lista de revisión antes de abrir el Pull Request

- [ ] La app está en `INSTALLED_APPS` y su `apps.py` dice `name = "apps.<app>"`.
- [ ] El modelo tiene `condominio` (o llega a él) y la migración está creada y subida.
- [ ] Cada vista tiene `RolRequeridoMixin` y, si lista/edita registros, `CondominioQuerysetMixin`.
- [ ] Los formularios limitan las listas desplegables al condominio activo y al usuario.
- [ ] Lo que el usuario no debe elegir (condominio, autor...) lo completa la vista en `form_valid`.
- [ ] Las plantillas extienden `base.html` y se ven bien en el celular.
- [ ] Hay pruebas y `python manage.py test apps` pasa completo.
- [ ] El código está comentado para que un compañero lo entienda.
