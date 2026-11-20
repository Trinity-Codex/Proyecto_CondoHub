"""
Vistas de mantenciones (Issue #123).

Permisos:
  - Ver el calendario:                         administrador, comité y conserje (el residente recibe 403)
  - Crear, editar y registrar ejecuciones:     solo el administrador
"""
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from apps.auditoria.servicios import Accion, registrar
from apps.core.listados import FiltrosGetMixin
from apps.core.permisos import ADMINISTRADOR, COMITE, CONSERJE, CondominioQuerysetMixin, RolRequeridoMixin

from .forms import EjecucionForm, MantencionForm
from .models import Mantencion

# Color de cada estado: reutiliza las insignias y chips que ya existen (.insignia-*, .chip-*).
COLOR_ESTADO = {
    Mantencion.Estado.AL_DIA: "al-dia",
    Mantencion.Estado.POR_VENCER: "con-deuda",  # naranja de «atención»
    Mantencion.Estado.VENCIDA: "moroso",  # rojo
}


def datos_auditados(mantencion):
    """Los campos que van a auditoría, en tipos que JSON entiende (fechas en texto)."""
    return {
        "nombre": mantencion.nombre,
        "frecuencia_meses": mantencion.frecuencia_meses,
        "proxima_fecha": mantencion.proxima_fecha.isoformat(),
        "proveedor_id": mantencion.proveedor_id,
        "dias_anticipacion": mantencion.dias_anticipacion,
    }


class MantencionListView(FiltrosGetMixin, RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """
    Calendario por urgencia: lo vencido primero y luego por próxima fecha (que es lo mismo que ordenar por la fecha:
    las más antiguas son las vencidas).

    # ponytail: el estado depende de la fecha de hoy y de la anticipación de cada fila, así que se calcula en Python
    # sobre la lista completa del condominio (decenas de filas, sin paginar). Si pasara de unos cientos, pasar el
    # cálculo a la base de datos y paginar.

    """

    roles_permitidos = [ADMINISTRADOR, COMITE, CONSERJE]
    model = Mantencion
    template_name = "mantenciones/lista.html"
    context_object_name = "mantenciones"
    parametros_filtro = {"estado": Mantencion.Estado.values}

    # @spec:mantenciones-calendario-de-mantenciones
    def get_queryset(self):
        hoy = timezone.localdate()
        todas = list(super().get_queryset().select_related("proveedor").order_by("proxima_fecha", "nombre", "pk"))
        for m in todas:
            m.estado_hoy = m.estado_en(hoy)
            m.color_estado = COLOR_ESTADO[m.estado_hoy]
            m.dias_restantes = (m.proxima_fecha - hoy).days  # negativo = días de atraso
            m.dias_abs = abs(m.dias_restantes)  # para el texto «Hace 3 días» / «En 1 día»
        self.todas = todas  # los chips cuentan sobre todas, antes de filtrar
        elegido = self.filtro("estado")
        return [m for m in todas if m.estado_hoy == elegido] if elegido else todas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        cantidades = {estado: 0 for estado in Mantencion.Estado.values}
        for m in self.todas:
            cantidades[m.estado_hoy] += 1
        # Orden de los chips: de lo más urgente a lo más tranquilo.
        opciones = [
            (estado, estado.label, COLOR_ESTADO[estado])
            for estado in (Mantencion.Estado.VENCIDA, Mantencion.Estado.POR_VENCER, Mantencion.Estado.AL_DIA)
        ]
        contexto["chips"] = self.chips(
            "estado", opciones, cantidades, singular="mantención", plural="mantenciones", total=len(self.todas),
        )
        return contexto


class MantencionFormMixin:
    """Lo que comparten crear y editar."""

    model = Mantencion
    form_class = MantencionForm
    template_name = "mantenciones/formulario.html"
    success_url = reverse_lazy("mantenciones:lista")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio  # filtra los proveedores del formulario
        return kwargs


class MantencionCreateView(RolRequeridoMixin, CondominioQuerysetMixin, MantencionFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    # @spec:mantenciones-calendario-de-mantenciones
    def form_valid(self, form):
        # El condominio NUNCA viene del formulario: lo pone la vista.
        form.instance.condominio = self.request.condominio
        with transaction.atomic():  # el alta y su registro de auditoría se guardan juntos o no se guardan
            respuesta = super().form_valid(form)
            registrar(
                self.request.user, self.request.condominio, Accion.CREAR, self.object,
                despues=datos_auditados(self.object),
            )
        messages.success(self.request, "Mantención registrada.")
        return respuesta


class MantencionUpdateView(RolRequeridoMixin, MantencionFormMixin, CondominioQuerysetMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]

    def get_object(self, queryset=None):
        mantencion = super().get_object(queryset)
        # Foto de los valores ANTES de que el formulario los pise: validar el form ya modifica la instancia.
        self.antes = datos_auditados(mantencion)
        return mantencion

    # @spec:mantenciones-calendario-de-mantenciones
    def form_valid(self, form):
        with transaction.atomic():
            respuesta = super().form_valid(form)
            despues = datos_auditados(self.object)
            if despues != self.antes:  # guardar sin cambiar nada no deja un registro vacío
                registrar(
                    self.request.user, self.request.condominio, Accion.MODIFICAR, self.object,
                    antes=self.antes, despues=despues,
                )
        messages.success(self.request, "Mantención actualizada.")
        return respuesta

    def form_invalid(self, form):
        # Formulario viejo: se vuelve por GET para ver la fecha recalculada. Recargar la respuesta de un POST
        # reenviaría los mismos datos viejos y el error se repetiría.
        if getattr(form, "desactualizado", False):
            messages.error(self.request, form.non_field_errors()[0])
            return HttpResponseRedirect(self.request.path)
        return super().form_invalid(form)


class EjecucionCreateView(RolRequeridoMixin, CondominioQuerysetMixin, SingleObjectMixin, FormView):
    """Registra que se hizo una mantención y recalcula su próxima fecha. La mantención sale del condominio activo (404 si no)."""

    roles_permitidos = [ADMINISTRADOR]
    model = Mantencion
    form_class = EjecucionForm
    template_name = "mantenciones/ejecucion_formulario.html"
    success_url = reverse_lazy("mantenciones:lista")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        return {"fecha": timezone.localdate()}

    # @spec:mantenciones-calendario-de-mantenciones
    def form_valid(self, form):
        self.object.registrar_ejecucion(
            self.request.user, form.cleaned_data["fecha"], form.cleaned_data["observacion"],
        )
        messages.success(
            self.request,
            f"Ejecución registrada. La próxima fecha de «{self.object}» es el {self.object.proxima_fecha:%d-%m-%Y}.",
        )
        return super().form_valid(form)
