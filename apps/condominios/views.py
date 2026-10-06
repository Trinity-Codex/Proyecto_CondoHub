"""
Vistas de edificios, unidades y residentes (RF01).

En la base solo hay una vista de CONSULTA para el administrador y el comité.
Crear y editar edificios, unidades y residentes desde el sitio es una feature
del backlog (por ahora se hace desde /admin/ con el superusuario o con el
comando "cargar_demo").
"""
from django.db.models import Prefetch
from django.views.generic import ListView

from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin

from .models import Edificio, Residente


class UnidadesView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Edificios del condominio con sus unidades y residentes."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = Edificio
    template_name = "condominios/unidades.html"
    context_object_name = "edificios"

    def get_queryset(self):
        # prefetch_related trae unidades y residentes en pocas consultas (no una por unidad).
        residentes = Residente.objects.filter(activo=True).select_related("usuario")
        return super().get_queryset().prefetch_related(
            "unidades", Prefetch("unidades__residentes", queryset=residentes)
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["suma_alicuotas"] = self.request.condominio.suma_alicuotas()
        return contexto
