"""
Vistas de comunicados (RF09). MÓDULO DE REFERENCIA: se usa como ejemplo en
docs/GUIA_NUEVA_FEATURE.md para construir módulos nuevos con el mismo patrón.

Se usan VISTAS BASADAS EN CLASES genéricas de Django (ListView, DetailView,
CreateView...), que ya traen el trabajo repetitivo hecho. Cada vista combina:
  1. RolRequeridoMixin       -> quién puede entrar (roles_permitidos)
  2. CondominioQuerysetMixin -> solo registros del condominio activo
  3. la vista genérica       -> qué hace (listar, ver, crear, editar, eliminar)

Permisos:
  - Listar y ver:                  cualquier miembro del condominio
  - Crear, editar y eliminar:      administrador
"""
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.permisos import (
    ADMINISTRADOR,
    COMITE,
    CONSERJE,
    CondominioQuerysetMixin,
    RolRequeridoMixin,
    tiene_rol,
)

from .forms import ComunicadoForm
from .models import Comunicado


class ComunicadosVisiblesMixin(CondominioQuerysetMixin):
    """
    Un residente ve los comunicados generales y los de SUS edificios.
    El administrador, el comité y el conserje ven todos los del condominio.
    """

    def get_queryset(self):
        qs = super().get_queryset().select_related("autor", "edificio")
        if tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE):
            return qs
        mis_edificios = self.request.user.residencias.filter(activo=True).values("unidad__edificio")
        return qs.filter(Q(tipo=Comunicado.Tipo.GENERAL) | Q(edificio__in=mis_edificios))


class ComunicadoListView(RolRequeridoMixin, ComunicadosVisiblesMixin, ListView):
    model = Comunicado
    template_name = "comunicados/lista.html"
    context_object_name = "comunicados"
    paginate_by = 10  # 10 comunicados por página


class ComunicadoDetailView(RolRequeridoMixin, ComunicadosVisiblesMixin, DetailView):
    model = Comunicado
    template_name = "comunicados/detalle.html"
    context_object_name = "comunicado"


class ComunicadoFormMixin:
    """Lo que comparten crear y editar: formulario, plantilla y condominio activo."""

    model = Comunicado
    form_class = ComunicadoForm
    template_name = "comunicados/formulario.html"

    def get_form_kwargs(self):
        # Le pasamos el condominio activo al formulario (ver ComunicadoForm.__init__).
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs


class ComunicadoCreateView(RolRequeridoMixin, ComunicadoFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        """Se ejecuta cuando el formulario es válido: completamos lo que no llena el usuario."""
        comunicado = form.save(commit=False)  # crea el objeto SIN guardarlo todavía
        comunicado.condominio = self.request.condominio
        comunicado.autor = self.request.user
        comunicado.publicar()  # guarda y notifica a los residentes (patrón Observer)
        self.object = comunicado
        messages.success(self.request, "Comunicado publicado y notificado a los residentes.")
        return super().form_valid(form)


class ComunicadoUpdateView(RolRequeridoMixin, ComunicadoFormMixin, CondominioQuerysetMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        messages.success(self.request, "Comunicado actualizado.")
        return super().form_valid(form)


class ComunicadoDeleteView(RolRequeridoMixin, CondominioQuerysetMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    model = Comunicado
    template_name = "comunicados/confirmar_eliminar.html"
    success_url = reverse_lazy("comunicados:lista")

    def form_valid(self, form):
        messages.success(self.request, "Comunicado eliminado.")
        return super().form_valid(form)
