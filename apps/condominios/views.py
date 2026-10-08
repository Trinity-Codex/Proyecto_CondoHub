"""
Vistas de edificios, unidades y residentes (RF01, Issue #10).

Permisos:
  - Ver edificios, unidades y residentes:              administrador y comité
  - Crear/editar/eliminar edificios y unidades,
    asignar residentes y darlos de baja:               administrador
  - Residentes y conserje:                             sin acceso (403)

Todo se trabaja desde la página Unidades: las acciones vuelven a ella.
"""
from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin

from .forms import EdificioForm, ResidenteForm, UnidadForm
from .models import Edificio, Residente, Unidad


def url_unidades(edificio=None):
    """Página Unidades; con edificio, baja directo hasta su tarjeta."""
    url = reverse("condominios:unidades")
    return f"{url}#edificio-{edificio.pk}" if edificio else url


def avisar_si_alicuotas_descuadradas(request):
    """Después de un cambio en las unidades, avisa si las alícuotas ya no suman 1 (100 %)."""
    suma = request.condominio.suma_alicuotas()
    if suma != 1:
        messages.warning(
            request,
            f"Las alícuotas del condominio suman {suma:.6f} y deberían sumar 1. "
            "Ajústalas para que el prorrateo de los gastos comunes reparta el total exacto.",
        )


class UnidadesView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Edificios del condominio con sus unidades y residentes."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = Edificio
    template_name = "condominios/unidades.html"
    context_object_name = "edificios"

    def get_queryset(self):
        # prefetch_related trae unidades y residentes en pocas consultas (no una por unidad).
        residentes = Residente.objects.filter(activo=True).select_related("usuario")
        return super().get_queryset().prefetch_related(
            "unidades", Prefetch("unidades__residentes", queryset=residentes)
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["suma_alicuotas"] = self.request.condominio.suma_alicuotas()
        return contexto


class EliminarConMotivosMixin:
    """
    Para eliminar edificios y unidades: si el objeto tiene datos que se
    perderían en cascada (ver motivos_para_no_eliminar() en el modelo), la
    página de confirmación lo explica y no se permite borrarlo.
    """

    template_name = "condominios/confirmar_eliminar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["motivos"] = self.object.motivos_para_no_eliminar()
        return contexto

    def form_valid(self, form):
        motivos = self.object.motivos_para_no_eliminar()
        if motivos:
            messages.error(self.request, f"No se puede eliminar {self.object}: {'; '.join(motivos)}.")
            return redirect(self.get_success_url())
        return super().form_valid(form)


# --------------------------------------------------------------------------
# Edificios
# --------------------------------------------------------------------------
class EdificioFormMixin:
    """Lo que comparten crear y editar un edificio."""

    model = Edificio
    form_class = EdificioForm
    template_name = "condominios/formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def get_success_url(self):
        return url_unidades(self.object)


class EdificioCreateView(RolRequeridoMixin, EdificioFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    extra_context = {"titulo": "Nuevo edificio"}

    def form_valid(self, form):
        form.instance.condominio = self.request.condominio
        messages.success(self.request, f"Edificio «{form.instance.nombre}» creado. Ahora agrega sus unidades.")
        return super().form_valid(form)


class EdificioUpdateView(RolRequeridoMixin, CondominioQuerysetMixin, EdificioFormMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]
    extra_context = {"titulo": "Editar edificio"}

    def form_valid(self, form):
        messages.success(self.request, "Edificio actualizado.")
        return super().form_valid(form)


class EdificioDeleteView(RolRequeridoMixin, CondominioQuerysetMixin, EliminarConMotivosMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    model = Edificio

    def get_success_url(self):
        return url_unidades()

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        if not self.object.pk:  # pk = None: se eliminó de verdad
            messages.success(self.request, "Edificio eliminado.")
        return respuesta


# --------------------------------------------------------------------------
# Unidades
# --------------------------------------------------------------------------
class UnidadFormMixin:
    """Lo que comparten crear y editar una unidad."""

    model = Unidad
    form_class = UnidadForm
    template_name = "condominios/formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def get_success_url(self):
        return url_unidades(self.object.edificio)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        avisar_si_alicuotas_descuadradas(self.request)
        return respuesta


class UnidadCreateView(RolRequeridoMixin, UnidadFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    extra_context = {"titulo": "Nueva unidad"}

    def get_initial(self):
        """Desde el botón "Agregar unidad" de un edificio, ese edificio viene elegido (?edificio=<id>)."""
        return {"edificio": self.request.GET.get("edificio")}

    def form_valid(self, form):
        messages.success(self.request, f"Unidad {form.instance.numero} creada.")
        return super().form_valid(form)


class UnidadUpdateView(RolRequeridoMixin, CondominioQuerysetMixin, UnidadFormMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]
    campo_condominio = "edificio__condominio"
    extra_context = {"titulo": "Editar unidad"}

    def form_valid(self, form):
        messages.success(self.request, f"Unidad {form.instance.numero} actualizada.")
        return super().form_valid(form)


class UnidadDeleteView(RolRequeridoMixin, CondominioQuerysetMixin, EliminarConMotivosMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    model = Unidad
    campo_condominio = "edificio__condominio"

    def get_success_url(self):
        return url_unidades(self.object.edificio)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        if not self.object.pk:
            messages.success(self.request, "Unidad eliminada.")
            avisar_si_alicuotas_descuadradas(self.request)
        return respuesta


# --------------------------------------------------------------------------
# Residentes
# --------------------------------------------------------------------------
class ResidenteCreateView(RolRequeridoMixin, FormView):
    """Asignar un residente a una unidad (buscando su cuenta por correo)."""

    roles_permitidos = [ADMINISTRADOR]
    form_class = ResidenteForm
    template_name = "condominios/formulario.html"

    def get_unidad(self):
        # Solo unidades del condominio activo: la de otro condominio responde 404.
        if not hasattr(self, "_unidad"):
            self._unidad = get_object_or_404(
                Unidad.objects.select_related("edificio"),
                pk=self.kwargs["unidad_pk"],
                edificio__condominio=self.request.condominio,
            )
        return self._unidad

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["unidad"] = self.get_unidad()
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Agregar residente a {self.get_unidad()}"
        return contexto

    def form_valid(self, form):
        residente = form.save()
        messages.success(self.request, f"{residente.usuario} quedó como {residente.get_tipo_display().lower()} de {residente.unidad}.")
        return redirect(url_unidades(residente.unidad.edificio))


class ResidenteBajaView(RolRequeridoMixin, View):
    """Dar de baja a un residente (solo por POST, desde el botón de la página Unidades)."""

    roles_permitidos = [ADMINISTRADOR]
    http_method_names = ["post"]

    def post(self, request, pk):
        residente = get_object_or_404(
            Residente.objects.select_related("usuario", "unidad__edificio"),
            pk=pk,
            activo=True,
            unidad__edificio__condominio=request.condominio,
        )
        residente.dar_de_baja()
        messages.success(request, f"{residente.usuario} ya no es residente de {residente.unidad}.")
        return redirect(url_unidades(residente.unidad.edificio))
