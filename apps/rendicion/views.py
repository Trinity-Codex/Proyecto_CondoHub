from django.utils.cache import add_never_cache_headers
from django.utils.http import content_disposition_header
from django.views.generic import DetailView, ListView

from apps.core.pdf import renderizar_pdf
from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin
from apps.gastos.models import PeriodoGasto

from .consultas import rendicion_del_periodo


class PeriodosEmitidosMixin(RolRequeridoMixin, CondominioQuerysetMixin):
    roles_permitidos = [ADMINISTRADOR, COMITE]
    queryset = PeriodoGasto.objects.filter(estado=PeriodoGasto.Estado.EMITIDO).select_related("condominio")


class RendicionInicioView(PeriodosEmitidosMixin, ListView):
    template_name = "rendicion/inicio.html"
    context_object_name = "periodos"


class RendicionDetalleView(PeriodosEmitidosMixin, DetailView):
    template_name = "rendicion/detalle.html"
    context_object_name = "periodo"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **rendicion_del_periodo(self.object)}


class RendicionPDFView(RendicionDetalleView):
    def render_to_response(self, context, **kwargs):
        nombre = f"rendicion-{self.object.anio}-{self.object.mes:02d}.pdf"
        respuesta = renderizar_pdf("rendicion/pdf.html", context, nombre)
        respuesta["Content-Disposition"] = content_disposition_header(True, nombre)
        add_never_cache_headers(respuesta)
        return respuesta
