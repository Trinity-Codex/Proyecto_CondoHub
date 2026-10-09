"""
Vistas de pagos (Issues #3 y #4).

  - Residente: su estado de cuenta y el detalle de cada cobro (RF03).
  - Administrador: registra pagos desde el estado de cuenta de una unidad (RF04).
  - Comité: puede consultar la cobranza y las cuentas, pero no registrar pagos.

Regla multi-condominio: una unidad o cobro de otro condominio da 404.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import DetailView, FormView, TemplateView

from apps.condominios.models import Unidad
from apps.core.permisos import ADMINISTRADOR, COMITE, RESIDENTE, RolRequeridoMixin
from apps.gastos.models import DetalleGastoComun

from .consultas import cobros_del_residente, con_saldos, total_adeudado
from .forms import PagoForm
from .models import Pago


class EstadoCuentaView(RolRequeridoMixin, TemplateView):
    roles_permitidos = [RESIDENTE]
    template_name = "pagos/estado_cuenta.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        cobros = con_saldos(cobros_del_residente(self.request.user, self.request.condominio))
        contexto["cobros"] = cobros
        contexto["total_adeudado"] = total_adeudado(cobros)
        return contexto


class CobroDetailView(RolRequeridoMixin, DetailView):
    """Detalle de un período: egresos del condominio, cómo se calculó el monto y los pagos hechos."""

    roles_permitidos = [RESIDENTE]
    template_name = "pagos/detalle.html"
    context_object_name = "cobro"

    def get_queryset(self):
        # Mismo filtro que la lista: si el cobro no es del usuario, DetailView responde 404.
        return cobros_del_residente(self.request.user, self.request.condominio)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        periodo = self.object.periodo
        contexto["egresos"] = periodo.egresos.all()
        contexto["total_egresos"] = periodo.total_egresos()
        contexto["pagos"] = self.object.pagos.all()
        (cobro,) = con_saldos([self.object])
        contexto["pagado"], contexto["saldo"] = cobro.pagado, cobro.saldo
        return contexto


class CobranzaView(RolRequeridoMixin, TemplateView):
    """Todas las unidades del condominio con lo que deben (administrador y comité)."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    template_name = "pagos/cobranza.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        unidades = (
            Unidad.objects.filter(edificio__condominio=self.request.condominio)
            .select_related("edificio")
            .prefetch_related("cobros__pagos")
            .order_by("edificio__nombre", "numero")
        )
        filas = []
        for unidad in unidades:
            cobros = con_saldos(unidad.cobros.all())
            filas.append({"unidad": unidad, "deuda": total_adeudado(cobros), "cobros": len(cobros)})
        contexto["filas"] = filas
        contexto["deuda_total"] = sum(f["deuda"] for f in filas)
        return contexto


class CuentaUnidadView(RolRequeridoMixin, TemplateView):
    """Estado de cuenta de UNA unidad, visto por la administración. Desde aquí se registran los pagos."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    template_name = "pagos/cuenta_unidad.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Filtrar por el condominio activo: una unidad de otra comunidad da 404.
        unidad = get_object_or_404(
            Unidad.objects.select_related("edificio"), pk=self.kwargs["pk"], edificio__condominio=self.request.condominio
        )
        cobros = con_saldos(
            unidad.cobros.select_related("periodo").prefetch_related("pagos").order_by("-periodo__anio", "-periodo__mes")
        )
        contexto["unidad"] = unidad
        contexto["cobros"] = cobros
        contexto["total_adeudado"] = total_adeudado(cobros)
        return contexto


class RegistrarPagoView(RolRequeridoMixin, FormView):
    """Formulario para registrar un pago contra un cobro (solo el administrador)."""

    roles_permitidos = [ADMINISTRADOR]
    form_class = PagoForm
    template_name = "pagos/registrar_pago.html"

    @cached_property
    def detalle(self):
        return get_object_or_404(
            DetalleGastoComun.objects.select_related("periodo", "unidad__edificio").prefetch_related("pagos"),
            pk=self.kwargs["pk"],
            periodo__condominio=self.request.condominio,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["detalle"] = self.detalle
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["cobro"] = self.detalle
        contexto["saldo"] = contexto["form"].saldo
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            Pago.registrar(
                self.detalle,
                monto=datos["monto"],
                fecha=datos["fecha"],
                medio=datos["medio"],
                observacion=datos["observacion"],
                registrado_por=self.request.user,
            )
        except ValidationError as error:
            # Por ejemplo, otra persona registró un pago justo antes y el saldo cambió.
            form.add_error("monto", error)
            return self.form_invalid(form)
        messages.success(self.request, "Pago registrado. Se avisó a los residentes de la unidad.")
        return redirect(reverse("pagos:cuenta_unidad", args=[self.detalle.unidad_id]))
