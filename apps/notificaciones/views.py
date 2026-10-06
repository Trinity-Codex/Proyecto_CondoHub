"""Vistas de notificaciones del usuario (RF10)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from apps.core.permisos import RolRequeridoMixin

from .models import Notificacion


class NotificacionListView(RolRequeridoMixin, ListView):
    template_name = "notificaciones/lista.html"
    context_object_name = "notificaciones"
    paginate_by = 20

    def get_queryset(self):
        # Solo las del usuario y del condominio activo.
        return Notificacion.objects.filter(usuario=self.request.user, condominio=self.request.condominio)


@login_required
def abrir(request, pk):
    """Marca la notificación como leída y lleva a la página relacionada (comunicado, incidente...)."""
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=["leida"])
    # Solo se redirige a direcciones del propio sitio (evita redirecciones a webs externas).
    if notificacion.url and url_has_allowed_host_and_scheme(notificacion.url, allowed_hosts={request.get_host()}):
        return redirect(notificacion.url)
    return redirect("notificaciones:lista")


@login_required
@require_POST
def marcar_todas_leidas(request):
    Notificacion.objects.filter(usuario=request.user, condominio=request.condominio, leida=False).update(leida=True)
    return redirect("notificaciones:lista")
