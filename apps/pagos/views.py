"""
Vistas del estado de cuenta del residente (RF03).

Permisos: solo RESIDENTE. Un residente jamás ve cobros de unidades ajenas:
el detalle usa el mismo queryset filtrado, así que un cobro ajeno da 404.
"""
from django.views.generic import DetailView, TemplateView

from apps.core.permisos import RESIDENTE, RolRequeridoMixin

from .consultas import cobros_del_residente, total_adeudado


class EstadoCuentaView(RolRequeridoMixin, TemplateView):
    roles_permitidos = [RESIDENTE]
    template_name = "pagos/estado_cuenta.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        cobros = list(cobros_del_residente(self.request.user, self.request.condominio))
        contexto["cobros"] = cobros
        contexto["total_adeudado"] = total_adeudado(cobros)
        return contexto


class CobroDetailView(RolRequeridoMixin, DetailView):
    """Detalle de un período: egresos del condominio y cómo se calculó el monto de la unidad."""

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
        return contexto     