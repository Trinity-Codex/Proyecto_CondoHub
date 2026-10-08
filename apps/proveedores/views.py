"""
Vistas de proveedores.

Permisos:
  - Ver la lista:                       administrador y comité
  - Crear, editar y activar/desactivar: solo el administrador
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin

from .forms import ProveedorForm
from .models import Proveedor


class ProveedorListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = Proveedor
    template_name = "proveedores/lista.html"
    context_object_name = "proveedores"
    paginate_by = 15

    def get_queryset(self):
        # Primero los activos, luego por nombre.
        return super().get_queryset().order_by("-activo", "razon_social")


class ProveedorFormMixin:
    """Lo que comparten crear y editar."""

    model = Proveedor
    form_class = ProveedorForm
    template_name = "proveedores/formulario.html"
    success_url = reverse_lazy("proveedores:lista")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio  # lo necesita clean_rut()
        return kwargs


class ProveedorCreateView(RolRequeridoMixin, ProveedorFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        # El condominio NUNCA viene del formulario: lo pone la vista.
        form.instance.condominio = self.request.condominio
        messages.success(self.request, "Proveedor registrado.")
        return super().form_valid(form)


class ProveedorUpdateView(RolRequeridoMixin, ProveedorFormMixin, CondominioQuerysetMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        messages.success(self.request, "Proveedor actualizado.")
        return super().form_valid(form)


class ProveedorCambiarEstadoView(RolRequeridoMixin, View):
    """Activa o desactiva un proveedor. Solo acepta POST (un cambio de datos no va por GET)."""

    roles_permitidos = [ADMINISTRADOR]
    http_method_names = ["post"]

    def post(self, request, pk):
        # Filtrar por condominio evita tocar proveedores de otra comunidad (daría 404).
        proveedor = get_object_or_404(Proveedor, pk=pk, condominio=request.condominio)
        proveedor.activo = not proveedor.activo
        proveedor.save(update_fields=["activo"])
        estado = "activado" if proveedor.activo else "desactivado"
        messages.success(request, f"Proveedor {estado}.")
        return redirect("proveedores:lista")