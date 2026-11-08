"""
Vistas de privacidad (Issue #51, Ley 21.719).

Permisos:
  - Aviso de privacidad: público, sin sesión (es la ÚNICA vista sin RolRequeridoMixin
    ni LoginRequiredMixin: se debe poder leer antes de iniciar sesión).
  - Descargar mis datos: cualquier persona con sesión, solo los suyos (LoginRequiredMixin,
    como Mi perfil: son SUS datos, no datos de un condominio).
  - Presentar y ver mis solicitudes: cualquier miembro del condominio activo; solo las propias.
  - Ver las solicitudes del condominio y responderlas: administrador.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.permisos import ADMINISTRADOR, CondominioQuerysetMixin, RolRequeridoMixin

from .descarga import datos_de
from .forms import RespuestaForm, SolicitudForm
from .models import SolicitudTitular


class AvisoPrivacidadView(TemplateView):
    """Página pública: no muestra datos de ningún condominio, solo el texto del aviso."""

    template_name = "privacidad/aviso.html"


class DescargarMisDatosView(LoginRequiredMixin, View):
    def get(self, request):
        nombre = f"mis-datos-condohub-{timezone.localdate():%Y-%m-%d}.json"
        respuesta = JsonResponse(
            datos_de(request.user), encoder=DjangoJSONEncoder, json_dumps_params={"ensure_ascii": False, "indent": 2}
        )
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        add_never_cache_headers(respuesta)  # que ni el navegador ni un proxy guarden una copia
        return respuesta


class MisSolicitudesMixin(RolRequeridoMixin):
    """Solo las solicitudes de la persona en el condominio activo: una ajena da 404."""

    model = SolicitudTitular

    def get_queryset(self):
        return SolicitudTitular.objects.filter(usuario=self.request.user, condominio=self.request.condominio)


class MisSolicitudesView(MisSolicitudesMixin, ListView):
    template_name = "privacidad/mis_solicitudes.html"
    context_object_name = "solicitudes"


class SolicitudDetailView(MisSolicitudesMixin, DetailView):
    template_name = "privacidad/solicitud.html"
    context_object_name = "solicitud"


class SolicitudCreateView(RolRequeridoMixin, CreateView):
    model = SolicitudTitular
    form_class = SolicitudForm
    template_name = "privacidad/formulario.html"
    success_url = reverse_lazy("privacidad:mis_solicitudes")

    def form_valid(self, form):
        solicitud = form.save(commit=False)
        solicitud.usuario = self.request.user
        solicitud.condominio = self.request.condominio
        solicitud.presentar()  # guarda y avisa a la administración (Observer)
        messages.success(self.request, "Recibimos tu solicitud. La administración te responderá por aquí y te avisaremos.")
        return redirect(self.success_url)


class SolicitudesView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Solicitudes del condominio: primero las pendientes."""

    roles_permitidos = [ADMINISTRADOR]
    model = SolicitudTitular
    template_name = "privacidad/solicitudes.html"
    context_object_name = "solicitudes"

    def get_queryset(self):
        # "-estado": PENDIENTE va antes que CERRADA (orden alfabético inverso).
        return super().get_queryset().select_related("usuario").order_by("-estado", "-creada")


class ResponderSolicitudView(RolRequeridoMixin, CondominioQuerysetMixin, UpdateView):
    """Ver una solicitud del condominio y, si está pendiente, responderla y cerrarla."""

    roles_permitidos = [ADMINISTRADOR]
    model = SolicitudTitular
    form_class = RespuestaForm
    template_name = "privacidad/responder.html"
    context_object_name = "solicitud"
    success_url = reverse_lazy("privacidad:solicitudes")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.esta_pendiente:
            return self.ya_cerrada()
        return super().post(request, *args, **kwargs)

    def ya_cerrada(self):
        messages.error(self.request, "Esa solicitud ya estaba cerrada.")
        return redirect(self.success_url)

    def form_valid(self, form):
        # cerrar() guarda la respuesta, cierra y avisa a la persona (Observer).
        try:
            self.object.cerrar(form.cleaned_data["respuesta"], por=self.request.user)
        except ValueError:  # otro administrador la cerró mientras esta persona escribía
            return self.ya_cerrada()
        messages.success(self.request, "Solicitud respondida y cerrada. Le avisamos a la persona.")
        return redirect(self.success_url)
