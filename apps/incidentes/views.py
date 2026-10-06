"""
Vistas de incidentes (RF07 y RF08).

Permisos:
  - Reportar:                       residente
  - Ver lista y detalle:            el residente ve los suyos; administrador,
                                    comité y conserje ven todos
  - Cambiar estado:                 administrador y conserje
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, ListView

from apps.core.permisos import (
    ADMINISTRADOR,
    COMITE,
    CONSERJE,
    RESIDENTE,
    CondominioQuerysetMixin,
    RolRequeridoMixin,
    tiene_rol,
)

from .forms import CambiarEstadoForm, IncidenteForm
from .models import Incidente


class IncidentesVisiblesMixin(CondominioQuerysetMixin):
    """El equipo del condominio ve todos los incidentes; un residente, solo los que reportó."""

    def get_queryset(self):
        qs = super().get_queryset().select_related("reportado_por", "unidad__edificio")
        if tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE):
            return qs
        return qs.filter(reportado_por=self.request.user)


class IncidenteListView(RolRequeridoMixin, IncidentesVisiblesMixin, ListView):
    model = Incidente
    template_name = "incidentes/lista.html"
    context_object_name = "incidentes"
    paginate_by = 15

    def get_queryset(self):
        """Filtro opcional por estado: /incidentes/?estado=RECIBIDO"""
        qs = super().get_queryset()
        estado = self.request.GET.get("estado")
        if estado in Incidente.Estado.values:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["estados"] = Incidente.Estado.choices
        contexto["estado_actual"] = self.request.GET.get("estado", "")
        # Para que la paginación conserve el filtro (ver templates/_paginacion.html).
        contexto["filtros_url"] = f"estado={contexto['estado_actual']}" if contexto["estado_actual"] else ""
        return contexto


class IncidenteCreateView(RolRequeridoMixin, CreateView):
    roles_permitidos = [RESIDENTE]
    model = Incidente
    form_class = IncidenteForm
    template_name = "incidentes/formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def form_valid(self, form):
        incidente = form.save(commit=False)
        incidente.condominio = self.request.condominio
        incidente.reportado_por = self.request.user
        incidente.reportar()  # guarda y avisa a la administración (patrón Observer)
        messages.success(self.request, f"Incidente #{incidente.pk} reportado. Te avisaremos cuando cambie su estado.")
        return redirect(incidente)


class IncidenteDetailView(RolRequeridoMixin, IncidentesVisiblesMixin, DetailView):
    """Muestra el incidente. Si es administrador o conserje, además permite cambiar el estado (POST)."""

    model = Incidente
    template_name = "incidentes/detalle.html"
    context_object_name = "incidente"

    def puede_gestionar(self):
        return tiene_rol(self.request, ADMINISTRADOR, CONSERJE)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if self.puede_gestionar():
            contexto["form_estado"] = kwargs.get("form_estado") or CambiarEstadoForm(instance=self.object)
        return contexto

    def post(self, request, *args, **kwargs):
        """RF08: cambio de estado enviado desde el formulario del detalle."""
        self.object = self.get_object()
        if not self.puede_gestionar():
            messages.error(request, "No tienes permisos para cambiar el estado.")
            return redirect(self.object)
        # El formulario valida sobre una COPIA del incidente: si los datos no son
        # válidos, la página vuelve a mostrar el estado real y no el enviado.
        form = CambiarEstadoForm(request.POST, instance=Incidente.objects.get(pk=self.object.pk))
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_estado=form))
        self.object.cambiar_estado(form.cleaned_data["estado"], form.cleaned_data["respuesta"])
        messages.success(request, "Estado actualizado y notificado al residente.")
        return redirect(self.object)
