"""Vistas generales: panel de inicio, cambio de condominio y página "sin condominio"."""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.comunicados.models import Comunicado
from apps.condominios.models import Residente, Unidad
from apps.incidentes.models import Incidente
from apps.pagos.consultas import cobros_del_residente, total_adeudado
from apps.reservas.models import Reserva

from .permisos import ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE, RolRequeridoMixin, condominios_del_usuario, tiene_rol


class InicioView(RolRequeridoMixin, TemplateView):
    """
    Panel de inicio. Cada rol ve tarjetas distintas:
      - todos:        últimos comunicados
      - residente:    su deuda, sus próximas reservas y sus incidentes abiertos
      - admin/comité/conserje: resumen del condominio (unidades, incidentes, reservas de hoy)
    """

    template_name = "core/inicio.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        condominio = self.request.condominio
        usuario = self.request.user
        hoy = date.today()

        # Misma regla que la lista de comunicados: un residente solo ve los de su edificio.
        contexto["comunicados"] = Comunicado.objects.visibles_para(
            usuario, condominio, ve_todos=tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE)
        ).select_related("edificio")[:3]
        contexto["mis_reservas"] = Reserva.objects.filter(
            solicitante=usuario, espacio__condominio=condominio, fecha__gte=hoy, estado=Reserva.Estado.CONFIRMADA
        ).select_related("espacio", "unidad__edificio")[:5]
        contexto["mis_incidentes"] = Incidente.objects.filter(
            reportado_por=usuario, condominio=condominio
        ).exclude(estado=Incidente.Estado.RESUELTO)[:5]

        # Tarjeta "Mi deuda": solo la calculamos si el usuario es residente.
        if RESIDENTE in self.request.roles:
            contexto["mi_deuda"] = total_adeudado(cobros_del_residente(usuario, condominio))

        if tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE):
            unidades = Unidad.objects.filter(edificio__condominio=condominio)
            contexto["resumen"] = {
                "unidades": unidades.count(),
                "residentes": Residente.objects.filter(unidad__in=unidades, activo=True).count(),
                "incidentes_abiertos": Incidente.objects.filter(condominio=condominio)
                .exclude(estado=Incidente.Estado.RESUELTO)
                .count(),
                "reservas_hoy": Reserva.objects.filter(
                    espacio__condominio=condominio, fecha=hoy, estado=Reserva.Estado.CONFIRMADA
                ).count(),
            }
            # Aviso si las alícuotas no suman 100 % (el prorrateo quedaría descuadrado).
            contexto["suma_alicuotas"] = condominio.suma_alicuotas()
            # Incidentes por atender, para el equipo del condominio.
            contexto["incidentes_pendientes"] = (
                Incidente.objects.filter(condominio=condominio)
                .exclude(estado=Incidente.Estado.RESUELTO)
                .select_related("unidad__edificio")[:5]
            )
        return contexto


@login_required
@require_POST  # cambiar de condominio modifica la sesión: solo por POST (formulario del menú)
def cambiar_condominio(request, pk):
    """Cambia el condominio activo (guardado en la sesión), si el usuario tiene acceso a él."""
    condominio = get_object_or_404(condominios_del_usuario(request.user), pk=pk)
    request.session["condominio_id"] = condominio.pk
    return redirect("core:inicio")


@login_required
def sin_condominio(request):
    """Se muestra cuando el usuario no pertenece a ningún condominio activo."""
    if request.condominio is not None:
        return redirect("core:inicio")
    return render(request, "core/sin_condominio.html")