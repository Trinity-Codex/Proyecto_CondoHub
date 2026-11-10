"""
Vistas de comunicados (RF09). MÓDULO DE REFERENCIA: se usa como ejemplo en
docs/GUIA_NUEVA_FEATURE.md para construir módulos nuevos con el mismo patrón.

Se usan VISTAS BASADAS EN CLASES genéricas de Django (ListView, DetailView,
CreateView...), que ya traen el trabajo repetitivo hecho. Cada vista combina:
  1. RolRequeridoMixin       -> quién puede entrar (roles_permitidos)
  2. CondominioQuerysetMixin -> solo registros del condominio activo
  3. la vista genérica       -> qué hace (listar, ver, crear, editar, eliminar)

Permisos:
  - Listar y ver:                  cualquier miembro del condominio
  - Crear, editar y eliminar:      administrador
  - Marcar como leído:             residente al que va dirigido (Issue #58)
  - Ver las confirmaciones:        administrador (Issue #58)
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

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

from .forms import ComunicadoForm
from .models import Comunicado, LecturaComunicado


class ComunicadosVisiblesMixin(CondominioQuerysetMixin):
    """
    Un residente ve los comunicados generales y los de SUS edificios.
    El administrador, el comité y el conserje ven todos los del condominio.
    """

    def get_queryset(self):
        # La regla de visibilidad está en el modelo (ComunicadoQuerySet.visibles_para).
        return (
            super()
            .get_queryset()
            .visibles_para(
                self.request.user,
                self.request.condominio,
                ve_todos=tiene_rol(self.request, ADMINISTRADOR, COMITE, CONSERJE),
            )
            .select_related("autor", "edificio")
        )


class ComunicadoListView(RolRequeridoMixin, FiltrosGetMixin, ComunicadosVisiblesMixin, ListView):
    """
    Lista principal: solo los vigentes (RF13). Con ?vigencia=vencidos, los vencidos (Issue #58).
    Se usa un enlace y no chips: los chips traen «Todos» activo por defecto y aquí lo normal es
    ver solo los vigentes.
    """

    model = Comunicado
    template_name = "comunicados/lista.html"
    context_object_name = "comunicados"
    paginate_by = 10  # 10 comunicados por página
    parametros_filtro = {"vigencia": ["vencidos"]}

    def get_queryset(self):
        hoy = timezone.localdate()
        qs = super().get_queryset()
        return qs.vencidos(hoy) if self.filtro("vigencia") else qs.vigentes(hoy)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["ver_vencidos"] = bool(self.filtro("vigencia"))
        if not contexto["ver_vencidos"]:
            contexto["cantidad_vencidos"] = super().get_queryset().vencidos(timezone.localdate()).count()
        if tiene_rol(self.request, ADMINISTRADOR):
            # Conteo de lectura por unidad, solo de los comunicados de esta página.
            for comunicado in contexto["comunicados"]:
                confirmadas, destinatarias = comunicado.confirmaciones()
                comunicado.confirmadas, comunicado.destinatarias = len(confirmadas), len(destinatarias)
        return contexto


class ComunicadoDetailView(RolRequeridoMixin, ComunicadosVisiblesMixin, DetailView):
    """El detalle no filtra por vigencia: el enlace de una notificación antigua sigue funcionando."""

    model = Comunicado
    template_name = "comunicados/detalle.html"
    context_object_name = "comunicado"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        comunicado, usuario = self.object, self.request.user
        contexto["vencido"] = comunicado.esta_vencido(timezone.localdate())
        if tiene_rol(self.request, RESIDENTE):
            contexto["puede_marcar"] = True
            contexto["leido"] = comunicado.lecturas.filter(usuario=usuario).exists()
        if tiene_rol(self.request, ADMINISTRADOR):
            confirmadas, destinatarias = comunicado.confirmaciones()
            contexto["confirmadas"], contexto["destinatarias"] = len(confirmadas), len(destinatarias)
            contexto["faltan"] = sorted(destinatarias - confirmadas, key=lambda u: (u.edificio.nombre, u.piso, u.numero))
        return contexto


class MarcarLeidoView(RolRequeridoMixin, View):
    """
    El residente marca el comunicado como leído (Issue #58). Solo por POST. Si el comunicado no
    va dirigido a él (otro edificio u otro condominio), 404. Pulsar dos veces no duplica.
    """

    roles_permitidos = [RESIDENTE]
    http_method_names = ["post"]

    def post(self, request, pk):
        visibles = Comunicado.objects.visibles_para(request.user, request.condominio, ve_todos=False)
        comunicado = get_object_or_404(visibles, pk=pk)
        LecturaComunicado.objects.get_or_create(comunicado=comunicado, usuario=request.user)
        messages.success(request, "Marcaste el comunicado como leído. ¡Gracias!")
        return redirect(comunicado.get_absolute_url())


class ComunicadoFormMixin:
    """Lo que comparten crear y editar: formulario, plantilla y condominio activo."""

    model = Comunicado
    form_class = ComunicadoForm
    template_name = "comunicados/formulario.html"

    def get_form_kwargs(self):
        # Le pasamos el condominio activo al formulario (ver ComunicadoForm.__init__).
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs


class ComunicadoCreateView(RolRequeridoMixin, ComunicadoFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        """Se ejecuta cuando el formulario es válido: completamos lo que no llena el usuario."""
        comunicado = form.save(commit=False)  # crea el objeto SIN guardarlo todavía
        comunicado.condominio = self.request.condominio
        comunicado.autor = self.request.user
        comunicado.publicar()  # guarda y notifica a los residentes (patrón Observer)
        self.object = comunicado
        messages.success(self.request, "Comunicado publicado y notificado a los residentes.")
        return super().form_valid(form)


class ComunicadoUpdateView(RolRequeridoMixin, ComunicadoFormMixin, CondominioQuerysetMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]

    def form_valid(self, form):
        messages.success(self.request, "Comunicado actualizado.")
        return super().form_valid(form)


class ComunicadoDeleteView(RolRequeridoMixin, CondominioQuerysetMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    model = Comunicado
    template_name = "comunicados/confirmar_eliminar.html"
    success_url = reverse_lazy("comunicados:lista")

    def form_valid(self, form):
        messages.success(self.request, "Comunicado eliminado.")
        return super().form_valid(form)
