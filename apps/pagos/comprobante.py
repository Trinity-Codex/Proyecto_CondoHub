"""Descarga del comprobante de un pago registrado."""
from django.utils.cache import add_never_cache_headers
from django.utils.http import content_disposition_header
from django.views.generic import DetailView

from apps.core.pdf import renderizar_pdf
from apps.core.permisos import ADMINISTRADOR, RESIDENTE, CondominioQuerysetMixin, RolRequeridoMixin

from .consultas import cobros_del_residente, saldo_del_cobro
from .models import Pago


class ComprobantePagoView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    model = Pago
    campo_condominio = "detalle__periodo__condominio"
    roles_permitidos = [RESIDENTE, ADMINISTRADOR]

    def get_queryset(self):
        condominio = self.request.condominio
        pagos = super().get_queryset().filter(detalle__unidad__edificio__condominio=condominio)
        if ADMINISTRADOR not in self.request.roles:
            visibles = cobros_del_residente(self.request.user, condominio)
            pagos = pagos.filter(detalle_id__in=visibles.order_by().values("pk"))
        return pagos.select_related("detalle__unidad__edificio", "detalle__periodo__condominio")

    def get(self, request, *args, **kwargs):
        pago = self.get_object()
        nombre = f"comprobante-pago-{pago.pk}.pdf"
        respuesta = renderizar_pdf("pagos/pdf/comprobante.html", {
            "pago": pago, "cobro": pago.detalle, "saldo": saldo_del_cobro(pago.detalle),
        }, nombre)
        respuesta["Content-Disposition"] = content_disposition_header(True, nombre)
        add_never_cache_headers(respuesta)
        return respuesta
