"""
Vistas de incidentes (RF07 y RF08).

Permisos:
  - Reportar:                       residente
  - Ver lista y detalle:            el residente ve los suyos; administrador,
                                    comité y conserje ven todos
  - Cambiar estado:                 administrador y conserje
  - Fotos de respaldo (Issue #122): las ve quien ve el incidente; el residente sube las «antes»
                                    al reportar; administrador y conserje suben las «después» y borran
"""
import mimetypes

from django.contrib import messages
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Q, When
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.utils.cache import patch_cache_control
from django.views import View
from django.views.generic import CreateView, DetailView, ListView
from django.views.generic.detail import SingleObjectMixin

from apps.core.listados import FiltrosGetMixin
from apps.core.permisos import (
    ADMINISTRADOR,
    COMITE,
    CONSERJE,
    RESIDENTE,
    CondominioQuerysetMixin,
    RolRequeridoMixin,
    tiene_rol,
)

from .forms import CambiarEstadoForm, FotosDespuesForm, IncidenteForm
from .models import FotoIncidente, Incidente


class IncidentesVisiblesMixin(CondominioQuerysetMixin):
    """El equipo del condominio ve todos los incidentes; un residente, solo los que reportó."""

    def get_queryset(self):
        qs = super().get_queryset().select_related("reportado_por", "unidad__edificio")
        if tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE):
            return qs
        return qs.filter(reportado_por=self.request.user)


def por_urgencia():
    """
    Orden de la lista (Issue #80): primero lo que requiere acción. Recibidos, en proceso y resueltos;
    entre los abiertos el más antiguo primero (lleva más tiempo esperando) y entre los resueltos el más reciente.
    """
    rango = Case(
        When(estado=Incidente.Estado.RECIBIDO, then=0),
        When(estado=Incidente.Estado.EN_PROCESO, then=1),
        default=2,
        output_field=IntegerField(),
    )
    # Cada grupo usa solo una de las dos fechas (la otra es NULL en todo el grupo), así se mezclan sin choques.
    abiertos = Case(When(~Q(estado=Incidente.Estado.RESUELTO), then=F("fecha_reporte")))
    resueltos = Case(When(estado=Incidente.Estado.RESUELTO, then=F("fecha_reporte")))
    return [rango, abiertos.asc(), resueltos.desc(), "-pk"]


# (valor, texto, clave de color) de cada chip; el color sale de la paleta --estado-*.
COLORES_ESTADO = {
    Incidente.Estado.RECIBIDO: "recibido",
    Incidente.Estado.EN_PROCESO: "en-proceso",
    Incidente.Estado.RESUELTO: "resuelto",
}


class IncidenteListView(FiltrosGetMixin, RolRequeridoMixin, IncidentesVisiblesMixin, ListView):
    model = Incidente
    template_name = "incidentes/lista.html"
    context_object_name = "incidentes"
    paginate_by = 15
    parametros_filtro = {"estado": Incidente.Estado.values}

    def visibles(self):
        """Lo que el rol puede ver en el condominio activo, sin filtrar ni ordenar."""
        return super().get_queryset()

    def get_queryset(self):
        """Filtro opcional por estado (/incidentes/?estado=RECIBIDO) y orden por urgencia."""
        qs = self.visibles()
        estado = self.filtro("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs.order_by(*por_urgencia())

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Una sola consulta cuenta todos los estados, antes de filtrar y sobre lo que este rol puede ver.
        cantidades = dict(self.visibles().order_by().values_list("estado").annotate(n=Count("pk")))
        opciones = [(valor, texto, COLORES_ESTADO[valor]) for valor, texto in Incidente.Estado.choices]
        contexto["chips"] = self.chips("estado", opciones, cantidades, singular="incidente", plural="incidentes")
        return contexto


class IncidenteCreateView(RolRequeridoMixin, CreateView):
    roles_permitidos = [RESIDENTE]
    model = Incidente
    form_class = IncidenteForm
    template_name = "incidentes/formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def form_valid(self, form):
        incidente = form.save(commit=False)
        incidente.condominio = self.request.condominio
        incidente.reportado_por = self.request.user
        # Incidente y fotos «antes» se guardan juntos: si una foto falla, no queda un reporte a medias.
        with transaction.atomic():
            incidente.reportar()  # guarda y avisa a la administración (patrón Observer)
            FotoIncidente.subir(incidente, form.cleaned_data["fotos"], FotoIncidente.Etapa.ANTES, self.request.user)
        messages.success(self.request, f"Incidente #{incidente.pk} reportado. Te avisaremos cuando cambie su estado.")
        return redirect(incidente)


class IncidenteDetailView(RolRequeridoMixin, IncidentesVisiblesMixin, DetailView):
    """Muestra el incidente. Si es administrador o conserje, además permite cambiar el estado (POST)."""

    model = Incidente
    template_name = "incidentes/detalle.html"
    context_object_name = "incidente"

    def puede_gestionar(self):
        return tiene_rol(self.request, ADMINISTRADOR, CONSERJE)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if self.puede_gestionar():
            contexto["form_estado"] = kwargs.get("form_estado") or CambiarEstadoForm(instance=self.object)
            contexto["form_fotos"] = FotosDespuesForm()
        # @spec:incidentes-fotos-de-respaldo: si puede ver el incidente, ve todas sus fotos (mismas reglas de visibilidad).
        fotos = list(self.object.fotos.select_related("subido_por"))
        contexto["fotos_antes"] = [f for f in fotos if f.etapa == FotoIncidente.Etapa.ANTES]
        contexto["fotos_despues"] = [f for f in fotos if f.etapa == FotoIncidente.Etapa.DESPUES]
        return contexto

    def post(self, request, *args, **kwargs):
        """RF08: cambio de estado enviado desde el formulario del detalle."""
        self.object = self.get_object()
        if not self.puede_gestionar():
            messages.error(request, "No tienes permisos para cambiar el estado.")
            return redirect(self.object)
        # El formulario valida sobre una COPIA del incidente: si los datos no son
        # válidos, la página vuelve a mostrar el estado real y no el enviado.
        form = CambiarEstadoForm(request.POST, instance=Incidente.objects.get(pk=self.object.pk))
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_estado=form))
        self.object.cambiar_estado(form.cleaned_data["estado"], form.cleaned_data["respuesta"], usuario=request.user)
        messages.success(request, "Estado actualizado y notificado al residente.")
        return redirect(self.object)


class FotoSubirView(RolRequeridoMixin, CondominioQuerysetMixin, SingleObjectMixin, View):
    """Administrador y conserje suben fotos «después» a un incidente de su condominio (solo POST)."""

    roles_permitidos = [ADMINISTRADOR, CONSERJE]
    model = Incidente
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        # @spec:incidentes-fotos-de-respaldo
        incidente = self.get_object()  # 404 si el incidente es de otro condominio
        form = FotosDespuesForm(request.POST, request.FILES, existentes=incidente.fotos.count())
        if form.is_valid():
            fotos = FotoIncidente.subir(incidente, form.cleaned_data["fotos"], FotoIncidente.Etapa.DESPUES, request.user)
            messages.success(request, f"Se subieron {len(fotos)} foto(s) al incidente #{incidente.pk}.")
        else:
            for error in form.errors["fotos"]:
                messages.error(request, error)
        return redirect(incidente)


class FotoBorrarView(RolRequeridoMixin, CondominioQuerysetMixin, SingleObjectMixin, View):
    """Solo administrador y conserje borran fotos (solo POST); la baja queda en auditoría."""

    roles_permitidos = [ADMINISTRADOR, CONSERJE]
    model = FotoIncidente
    campo_condominio = "incidente__condominio"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        # @spec:incidentes-fotos-de-respaldo
        foto = self.get_object()
        incidente = foto.incidente
        foto.eliminar(request.user)
        messages.success(request, "Foto eliminada.")
        return redirect(incidente)


class FotoArchivoView(RolRequeridoMixin, CondominioQuerysetMixin, SingleObjectMixin, View):
    """
    Entrega el archivo de la foto. No se sirve por MEDIA_URL: aquí se aplican las mismas reglas
    del incidente, así que pedir la URL directa sin permiso da 404 (otro condominio u otro residente).
    """

    roles_permitidos = [ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE]
    model = FotoIncidente
    campo_condominio = "incidente__condominio"

    def get_queryset(self):
        qs = super().get_queryset()
        if tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE):
            return qs
        return qs.filter(incidente__reportado_por=self.request.user)

    def get(self, request, *args, **kwargs):
        # @spec:incidentes-fotos-de-respaldo y @spec:incidentes-visibilidad-de-incidentes: mismas reglas de visibilidad que el incidente
        foto = self.get_object()
        try:
            archivo = foto.imagen.open("rb")
        except FileNotFoundError:
            raise Http404("El archivo de la foto ya no existe.") from None
        tipo = mimetypes.guess_type(foto.imagen.name)[0] or "application/octet-stream"
        respuesta = FileResponse(archivo, content_type=tipo)
        respuesta["X-Content-Type-Options"] = "nosniff"
        patch_cache_control(respuesta, private=True)  # una foto de un incidente no debe quedar en cachés compartidas
        return respuesta
