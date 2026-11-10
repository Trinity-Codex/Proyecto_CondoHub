"""Vistas generales: panel de inicio, cambio de condominio y página "sin condominio"."""
from collections import Counter
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.cartera.permisos import condominios_de_cartera
from apps.comunicados.models import Comunicado
from apps.condominios.models import Residente, Unidad
from apps.incidentes.models import Incidente
from apps.gastos.filtros import SITUACIONES
from apps.pagos.consultas import cobros_del_residente, reporte_del_ultimo_periodo, total_adeudado
from apps.reservas.models import Reserva

from .permisos import ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE, RolRequeridoMixin, condominios_del_usuario, tiene_rol


class InicioView(RolRequeridoMixin, TemplateView):
    """
    Panel de inicio. Cada rol ve tarjetas distintas:
      - todos:        últimos comunicados
      - residente:    su deuda, sus próximas reservas y sus incidentes abiertos
      - admin/comité/conserje: resumen (unidades y residentes) y tarjetas por estado (Issue #79)
      - admin/comité:  tarjetas de unidades al día, con deuda y morosas, del reporte del último
                       período emitido (Issues #57 y #79); la cobranza está en la página Cobranza
    """

    template_name = "core/inicio.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        condominio = self.request.condominio
        usuario = self.request.user
        hoy = date.today()

        # Misma regla que la lista de comunicados: un residente solo ve los de su edificio.
        # Solo los vigentes (Issue #58): los vencidos quedan en "Ver vencidos" de la lista.
        contexto["comunicados"] = Comunicado.objects.visibles_para(
            usuario, condominio, ve_todos=tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE)
        ).vigentes(timezone.localdate()).select_related("edificio")[:3]
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
            }
            tarjetas = []
            # Tarjetas de unidades (Issues #57 y #79): solo administrador y comité (el conserje no ve dinero),
            # del último período emitido y con generar_reporte, para que coincidan siempre con el reporte.
            # La recaudación y la deuda están en la página Cobranza.
            if tiene_rol(self.request, ADMINISTRADOR, COMITE):
                reporte = reporte_del_ultimo_periodo(condominio)
                contexto["ve_unidades"] = True
                contexto["hay_periodo"] = reporte is not None
                if reporte:
                    tarjetas += _tarjetas_de_unidades(reporte)
            tarjetas += _tarjetas_de_incidentes_y_reservas(condominio, hoy)
            contexto["tarjetas"] = tarjetas
            # Aviso si las alícuotas no suman 100 % (el prorrateo quedaría descuadrado).
            contexto["suma_alicuotas"] = condominio.suma_alicuotas()
            # Incidentes por atender, para el equipo del condominio.
            contexto["incidentes_pendientes"] = (
                Incidente.objects.filter(condominio=condominio)
                .exclude(estado=Incidente.Estado.RESUELTO)
                .select_related("unidad__edificio")[:5]
            )
        return contexto


def _tarjeta(clave, icono, nombre, cantidad, singular, plural, frase, url):
    """`icono` es una clase de Bootstrap Icons, decorativa: el nombre accesible sale del texto."""
    return {
        "clave": clave, "icono": icono, "nombre": nombre, "cantidad": cantidad,
        "etiqueta": singular if cantidad == 1 else plural, "frase": frase, "url": url,
    }


def _tarjetas_de_unidades(reporte):
    """
    Unidades al día / con deuda / morosas del reporte de #57, sin recalcular la morosidad: se cuenta
    la `situacion` de cada fila, así las tres cifras suman las unidades del período y coinciden con el reporte.
    Cada tarjeta abre el reporte ya filtrado con `?situacion=` (Issue #80), con los mismos chips y cantidades.
    """
    por_situacion = Counter(fila.situacion for fila in reporte.filas)
    base = f"{reverse('gastos:reporte')}?periodo={reporte.periodo.pk}&situacion="
    periodo = str(reporte.periodo)
    return [
        _tarjeta("al-dia", "bi-check-circle", "Unidades al día", por_situacion[SITUACIONES["al_dia"]], "unidad", "unidades",
                 f"Sin deuda en {periodo}", base + "al_dia"),
        _tarjeta("con-deuda", "bi-hourglass-split", "Unidades con deuda", por_situacion[SITUACIONES["pendiente"]],
                 "unidad", "unidades", f"Deben solo {periodo}", base + "pendiente"),
        _tarjeta("moroso", "bi-exclamation-triangle", "Unidades morosas", por_situacion[SITUACIONES["morosa"]],
                 "unidad", "unidades", f"Con deuda anterior a {periodo}", base + "morosa"),
    ]


def _tarjetas_de_incidentes_y_reservas(condominio, hoy):
    """Incidentes recibidos y en proceso (una consulta) y reservas confirmadas desde hoy (otra)."""
    por_estado = dict(
        Incidente.objects.filter(condominio=condominio).values_list("estado").annotate(total=Count("pk"))
    )
    reservas = Reserva.objects.filter(
        espacio__condominio=condominio, fecha__gte=hoy, estado=Reserva.Estado.CONFIRMADA
    ).aggregate(proximas=Count("pk"), de_hoy=Count("pk", filter=Q(fecha=hoy)))
    lista = reverse("incidentes:lista")
    recibidos = por_estado.get(Incidente.Estado.RECIBIDO, 0)
    en_proceso = por_estado.get(Incidente.Estado.EN_PROCESO, 0)
    de_hoy = reservas["de_hoy"]
    return [
        _tarjeta("recibido", "bi-inbox", "Incidentes recibidos", recibidos, "incidente", "incidentes",
                 "Esperan atención", f"{lista}?estado={Incidente.Estado.RECIBIDO}"),
        _tarjeta("en-proceso", "bi-wrench", "Incidentes en proceso", en_proceso, "incidente", "incidentes",
                 "Se están atendiendo", f"{lista}?estado={Incidente.Estado.EN_PROCESO}"),
        _tarjeta("reserva", "bi-calendar-event", "Reservas próximas", reservas["proximas"], "reserva", "reservas",
                 f"{de_hoy} para hoy", reverse("reservas:todas")),
    ]


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
    # Un administrador general no tiene condominio activo: su página es la cartera (Issue #54).
    if condominios_de_cartera(request.user).exists():
        return redirect("cartera:inicio")
    return render(request, "core/sin_condominio.html")