"""Aviso de cobro por unidad y período (RF03, #6)."""

from django.db.models import Q
from django.utils.cache import add_never_cache_headers
from django.utils.http import content_disposition_header
from django.views.generic import DetailView

from apps.core.pdf import renderizar_pdf
from apps.core.permisos import ADMINISTRADOR, RESIDENTE, CondominioQuerysetMixin, RolRequeridoMixin
from apps.gastos.models import DetalleGastoComun, PeriodoGasto

from .consultas import cobros_del_residente, egresos_para_residente, pagado_del_cobro, saldo_del_cobro, total_adeudado
from apps.rendicion.consultas import caja_del_mes, saldo_fondo_del_periodo


class AvisoCobroView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    roles_permitidos = [ADMINISTRADOR, RESIDENTE]
    model = DetalleGastoComun
    campo_condominio = "periodo__condominio"

    def get_queryset(self):
        if ADMINISTRADOR in self.request.roles:
            return super().get_queryset().filter(
                periodo__estado=PeriodoGasto.Estado.EMITIDO,
                unidad__edificio__condominio=self.request.condominio,
            ).select_related("unidad__edificio", "periodo__condominio").prefetch_related("pagos")
        return cobros_del_residente(self.request.user, self.request.condominio)

    def get(self, request, *args, **kwargs):
        cobro = self.get_object()
        periodo = cobro.periodo
        anteriores = self.get_queryset().filter(unidad=cobro.unidad).filter(
            Q(periodo__anio__lt=periodo.anio) | Q(periodo__anio=periodo.anio, periodo__mes__lt=periodo.mes)
        )
        anterior = total_adeudado(anteriores)
        saldo = saldo_del_cobro(cobro)
        nombre = f"aviso-{periodo.anio}-{periodo.mes:02d}-unidad-{cobro.unidad_id}.pdf"
        respuesta = renderizar_pdf("pagos/pdf/aviso.html", {
            "cobro": cobro, "periodo": periodo, "egresos": egresos_para_residente(periodo),
            "anterior": anterior, "pagado": pagado_del_cobro(cobro), "saldo": saldo,
            "saldo_fondo": saldo_fondo_del_periodo(periodo),
            "total": anterior + saldo, "caja": caja_del_mes(periodo),
        }, nombre)
        respuesta["Content-Disposition"] = content_disposition_header(True, nombre)
        add_never_cache_headers(respuesta)
        return respuesta
