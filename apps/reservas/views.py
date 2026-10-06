"""
Vistas de reservas de espacios comunes (RF05 y RF06).

Permisos:
  - Ver espacios y su disponibilidad:     cualquier miembro del condominio
  - Reservar y ver "mis reservas":        residente
  - Cancelar una reserva:                 quien la hizo, o el administrador
  - Ver todas las reservas:               administrador, comité y conserje
  - Crear y editar espacios comunes:      administrador
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.permisos import (
    ADMINISTRADOR,
    COMITE,
    CONSERJE,
    RESIDENTE,
    CondominioQuerysetMixin,
    RolRequeridoMixin,
    tiene_rol,
)

from .forms import EspacioComunForm, FechaForm, ReservaForm
from .models import EspacioComun, Reserva


# --------------------------------------------------------------------------
# Espacios comunes
# --------------------------------------------------------------------------
class EspacioListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    model = EspacioComun
    template_name = "reservas/espacios.html"
    context_object_name = "espacios"

    def get_queryset(self):
        qs = super().get_queryset()
        # El administrador también ve los espacios desactivados (para reactivarlos).
        return qs if tiene_rol(self.request, ADMINISTRADOR) else qs.filter(activo=True)


class EspacioDetailView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    """RF05: disponibilidad de un espacio en una fecha (?fecha=AAAA-MM-DD, por defecto hoy)."""

    model = EspacioComun
    template_name = "reservas/espacio_detalle.html"
    context_object_name = "espacio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        form = FechaForm(self.request.GET or {"fecha": date.today()})
        fecha = form.cleaned_data["fecha"] if form.is_valid() else date.today()
        contexto["form_fecha"] = form
        contexto["fecha"] = fecha
        contexto["reservas_del_dia"] = self.object.reservas.filter(
            fecha=fecha, estado=Reserva.Estado.CONFIRMADA
        ).select_related("unidad__edificio")
        return contexto


class EspacioCreateView(RolRequeridoMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    model = EspacioComun
    form_class = EspacioComunForm
    template_name = "reservas/espacio_formulario.html"
    success_url = reverse_lazy("reservas:espacios")

    def form_valid(self, form):
        form.instance.condominio = self.request.condominio
        messages.success(self.request, "Espacio común creado.")
        return super().form_valid(form)


class EspacioUpdateView(RolRequeridoMixin, CondominioQuerysetMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]
    model = EspacioComun
    form_class = EspacioComunForm
    template_name = "reservas/espacio_formulario.html"
    success_url = reverse_lazy("reservas:espacios")

    def form_valid(self, form):
        messages.success(self.request, "Espacio común actualizado.")
        return super().form_valid(form)


# --------------------------------------------------------------------------
# Reservas
# --------------------------------------------------------------------------
class ReservaCreateView(RolRequeridoMixin, CreateView):
    roles_permitidos = [RESIDENTE]
    model = Reserva
    form_class = ReservaForm
    template_name = "reservas/reserva_formulario.html"
    success_url = reverse_lazy("reservas:mis_reservas")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def get_initial(self):
        """Si se llega desde un espacio (?espacio=3&fecha=...), el formulario viene prellenado."""
        return {"espacio": self.request.GET.get("espacio"), "fecha": self.request.GET.get("fecha")}

    def form_valid(self, form):
        reserva = form.save(commit=False)
        reserva.solicitante = self.request.user
        try:
            reserva.confirmar()  # vuelve a validar con el espacio bloqueado (evita dobles reservas)
        except ValidationError as error:
            # Otra persona reservó ese horario justo antes: se muestra como error del formulario.
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Reserva confirmada: {reserva}.")
        return redirect(self.success_url)


class MisReservasView(RolRequeridoMixin, ListView):
    roles_permitidos = [RESIDENTE]
    template_name = "reservas/mis_reservas.html"
    context_object_name = "reservas"
    paginate_by = 15

    def get_queryset(self):
        return (
            Reserva.objects.filter(solicitante=self.request.user, espacio__condominio=self.request.condominio)
            .select_related("espacio", "unidad__edificio")
            .order_by("-fecha", "-hora_inicio")
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["hoy"] = date.today()
        return contexto


class ReservaListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Todas las reservas desde hoy, para el equipo del condominio (ej. el conserje prepara el quincho)."""

    roles_permitidos = [ADMINISTRADOR, COMITE, CONSERJE]
    model = Reserva
    campo_condominio = "espacio__condominio"
    template_name = "reservas/todas.html"
    context_object_name = "reservas"
    paginate_by = 20

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(fecha__gte=date.today(), estado=Reserva.Estado.CONFIRMADA)
            .select_related("espacio", "unidad__edificio", "solicitante")
        )


@login_required
@require_POST
def cancelar_reserva(request, pk):
    """Cancela una reserva futura. Puede hacerlo quien la hizo o el administrador."""
    if request.condominio is None:
        return redirect("core:sin_condominio")
    reserva = get_object_or_404(Reserva, pk=pk, espacio__condominio=request.condominio)
    es_duenio = reserva.solicitante_id == request.user.pk
    if not (es_duenio or tiene_rol(request, ADMINISTRADOR)):
        messages.error(request, "No puedes cancelar esta reserva.")
    elif reserva.fecha < date.today() or reserva.estado != Reserva.Estado.CONFIRMADA:
        messages.error(request, "Solo se pueden cancelar reservas futuras y confirmadas.")
    else:
        reserva.cancelar()
        messages.success(request, "Reserva cancelada.")
    # "volver": página desde la que se canceló. Solo se acepta si es de este mismo
    # sitio; si no, alguien podría usar el enlace para llevar al usuario a otra web.
    volver = request.POST.get("volver", "")
    if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}):
        volver = reverse("reservas:mis_reservas")
    return redirect(volver)
