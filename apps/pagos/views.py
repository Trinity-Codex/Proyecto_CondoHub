"""
Vistas de pagos (Issues #3 y #4).

  - Residente: su estado de cuenta y el detalle de cada cobro (RF03).
  - Administrador: registra pagos desde el estado de cuenta de una unidad (RF04) y los anula (#53).
  - Comité: puede consultar la cobranza y las cuentas, pero no registrar pagos.

Regla multi-condominio: una unidad o cobro de otro condominio da 404.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from apps.condominios.models import Unidad
from apps.core.permisos import ADMINISTRADOR, COMITE, RESIDENTE, CondominioQuerysetMixin, RolRequeridoMixin
from apps.gastos.models import DetalleGastoComun

from .consultas import cobros_del_residente, con_saldos, reporte_del_ultimo_periodo, total_adeudado
from .forms import AnularPagoForm, PagoForm
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
        # Indicadores del último período emitido (Issue #57), los mismos números del reporte.
        contexto["cobranza"] = reporte_del_ultimo_periodo(self.request.condominio)
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


# @spec:pagos-anulacion-de-pagos
class AnularPagoView(RolRequeridoMixin, CondominioQuerysetMixin, SingleObjectMixin, FormView):
    """
    Anula un pago con un motivo obligatorio (Issue #53). Solo el administrador: el comité y
    el residente reciben 403. GET muestra la confirmación; la anulación ocurre solo por POST.
    """

    roles_permitidos = [ADMINISTRADOR]
    model = Pago
    # Pago no tiene campo condominio: se llega por el cobro. Un pago de otro condominio da 404.
    campo_condominio = "detalle__periodo__condominio"
    context_object_name = "pago"
    form_class = AnularPagoForm
    template_name = "pagos/anular_pago.html"

    def get_queryset(self):
        # Solo los vigentes: un pago ya anulado no se vuelve a anular (404).
        return super().get_queryset().vigentes().select_related("detalle__periodo", "detalle__unidad__edificio")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            self.object.anular(form.cleaned_data["motivo"], anulado_por=self.request.user)
        except ValidationError as error:
            # Por ejemplo, otra persona lo anuló justo antes.
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Pago anulado. Se avisó a los residentes de la unidad.")
        return redirect(reverse("pagos:cuenta_unidad", args=[self.object.detalle.unidad_id]))
