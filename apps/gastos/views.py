"""
Vistas de gastos comunes: períodos y egresos (Issue #1, RF02).

Permisos:
  - Ver períodos y egresos:                         administrador y comité
  - Abrir períodos y crear/editar/eliminar egresos: administrador
  - Residentes y conserje:                          sin acceso (403)

Los egresos solo se modifican mientras el período está ABIERTO. Una vez
EMITIDO (Issue #2) quedan bloqueados: cambiarlos descuadraría lo ya cobrado.
"""
from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin

from .forms import EgresoForm, PeriodoForm
from .models import Egreso, PeriodoGasto


# --------------------------------------------------------------------------
# Períodos
# --------------------------------------------------------------------------
class PeriodoListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Lista de períodos del condominio con su total y cantidad de egresos."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = PeriodoGasto
    template_name = "gastos/periodos.html"
    context_object_name = "periodos"
    paginate_by = 12  # un año por página

    def get_queryset(self):
        # annotate() calcula el total y la cantidad en la misma consulta (no una por período).
        return super().get_queryset().annotate(total=Sum("egresos__monto"), cantidad=Count("egresos"))


class PeriodoFormMixin:
    """Lo que comparten abrir y editar un período."""

    model = PeriodoGasto
    form_class = PeriodoForm
    template_name = "gastos/periodo_formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs


class PeriodoCreateView(RolRequeridoMixin, PeriodoFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    def get_initial(self):
        """Por defecto se propone el mes actual."""
        hoy = timezone.localdate()
        return {"mes": hoy.month, "anio": hoy.year}

    def form_valid(self, form):
        form.instance.condominio = self.request.condominio
        messages.success(self.request, f"Período {form.instance} abierto. Ya puedes registrar sus egresos.")
        return super().form_valid(form)  # redirige a get_absolute_url() del período


class PeriodoUpdateView(RolRequeridoMixin, CondominioQuerysetMixin, PeriodoFormMixin, UpdateView):
    """Corregir mes, año o % del fondo de reserva (solo si el período está abierto)."""

    roles_permitidos = [ADMINISTRADOR]

    def get_queryset(self):
        return super().get_queryset().filter(estado=PeriodoGasto.Estado.ABIERTO)  # emitido -> 404

    def form_valid(self, form):
        messages.success(self.request, "Período actualizado.")
        return super().form_valid(form)


class PeriodoDetailView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    """Detalle del período: egresos, total y subtotal por categoría."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = PeriodoGasto
    template_name = "gastos/periodo_detalle.html"
    context_object_name = "periodo"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        egresos = self.object.egresos.select_related("creado_por")
        total = self.object.total_egresos()
        contexto["egresos"] = egresos
        contexto["total"] = total
        # Subtotal por categoría, con su nombre legible y su porcentaje del total.
        nombres = dict(Egreso.Categoria.choices)
        contexto["por_categoria"] = [
            {
                "categoria": nombres[fila["categoria"]],
                "subtotal": fila["subtotal"],
                "porcentaje": round(fila["subtotal"] * 100 / total, 1) if total else 0,
            }
            for fila in egresos.values("categoria").annotate(subtotal=Sum("monto")).order_by("-subtotal")
        ]
        return contexto


# --------------------------------------------------------------------------
# Egresos
# --------------------------------------------------------------------------
class PeriodoAbiertoMixin:
    """
    Bloquea crear, editar o eliminar egresos de un período que ya no está abierto.
    Cada vista define get_periodo() para saber de qué período se trata.
    """

    def dispatch(self, request, *args, **kwargs):
        # RolRequeridoMixin (que va antes en la lista de clases) ya revisó la
        # sesión y el condominio activo; aquí se revisa el estado del período.
        if request.user.is_authenticated and request.condominio is not None:
            periodo = self.get_periodo()
            if not periodo.esta_abierto:
                messages.error(request, f"El período {periodo} ya fue emitido: sus egresos no se pueden modificar.")
                return redirect(periodo)
        return super().dispatch(request, *args, **kwargs)


class EgresoCreateView(RolRequeridoMixin, PeriodoAbiertoMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    model = Egreso
    form_class = EgresoForm
    template_name = "gastos/egreso_formulario.html"

    def get_periodo(self):
        # Solo períodos del condominio activo: el de otro condominio responde 404.
        if not hasattr(self, "_periodo"):
            self._periodo = get_object_or_404(PeriodoGasto, pk=self.kwargs["periodo_pk"], condominio=self.request.condominio)
        return self._periodo

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["periodo"] = self.get_periodo()
        return contexto

    def form_valid(self, form):
        form.instance.periodo = self.get_periodo()
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Egreso registrado.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_periodo().get_absolute_url()


class EgresoDelPeriodoMixin(CondominioQuerysetMixin):
    """Para editar y eliminar: el egreso debe ser de un período del condominio activo."""

    model = Egreso
    campo_condominio = "periodo__condominio"

    def get_periodo(self):
        return self.get_object().periodo

    def get_success_url(self):
        return self.object.periodo.get_absolute_url()


class EgresoUpdateView(RolRequeridoMixin, EgresoDelPeriodoMixin, PeriodoAbiertoMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]
    form_class = EgresoForm
    template_name = "gastos/egreso_formulario.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["periodo"] = self.object.periodo
        return contexto

    def form_valid(self, form):
        messages.success(self.request, "Egreso actualizado.")
        return super().form_valid(form)


class EgresoDeleteView(RolRequeridoMixin, EgresoDelPeriodoMixin, PeriodoAbiertoMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    template_name = "gastos/egreso_confirmar_eliminar.html"

    def form_valid(self, form):
        messages.success(self.request, "Egreso eliminado.")
        return super().form_valid(form)
