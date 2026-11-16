"""
Vistas de auditoria: registro de quién hizo qué y cuándo (Ley 21.719, Issue #27).

Solo lectura: el registro es inmutable, así que la vista no acepta nada más que GET.
Pueden verla el administrador y el comité; conserje y residente reciben 403.
"""
from django.views.generic import ListView

from apps.core.permisos import ADMINISTRADOR, COMITE, RolRequeridoMixin

from .forms import FiltroAuditoriaForm
from .models import RegistroAuditoria
from .servicios import Accion


class AuditoriaInicioView(RolRequeridoMixin, ListView):
    # No se usa CondominioQuerysetMixin: condominio_id no es FK (ver models.py), se filtra a mano.
    roles_permitidos = [ADMINISTRADOR, COMITE]
    http_method_names = ["get", "head", "options"]
    model = RegistroAuditoria
    template_name = "auditoria/lista.html"
    context_object_name = "registros"
    paginate_by = 50

    def get_filtro(self):
        # Se crea una sola vez por petición: lo usan get_queryset y get_context_data.
        if not hasattr(self, "_filtro"):
            self._filtro = FiltroAuditoriaForm(self.request.GET or None, condominio_id=self.request.condominio.pk)
        return self._filtro

    def get_queryset(self):
        # Primero el límite del condominio; los filtros siempre se aplican encima de él.
        qs = RegistroAuditoria.objects.filter(condominio_id=self.request.condominio.pk)
        filtro = self.get_filtro()
        # Un formulario inválido no filtra: se muestra todo y el formulario enseña sus errores.
        if not filtro.is_bound or not filtro.is_valid():
            return qs
        datos = filtro.cleaned_data
        if datos["desde"]:
            qs = qs.filter(creado__date__gte=datos["desde"])
        if datos["hasta"]:
            qs = qs.filter(creado__date__lte=datos["hasta"])
        if datos["usuario"]:
            qs = qs.filter(usuario_id=int(datos["usuario"]))
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["filtro"] = self.get_filtro()
        # Para que la paginación conserve los filtros sin repetir "page".
        consulta = self.request.GET.copy()
        consulta.pop("page", None)
        contexto["consulta"] = consulta.urlencode()
        # Se preparan los textos aquí y no en la plantilla: la etiqueta de la acción y la lista
        # de campos "antes → después" (las claves vienen de uno u otro diccionario, o de ambos).
        etiquetas = dict(Accion.choices)
        registros = list(contexto["registros"])
        for r in registros:
            r.accion_texto = etiquetas.get(r.accion, r.accion)
            antes, despues = r.antes or {}, r.despues or {}
            r.cambios = [(c, antes.get(c), despues.get(c)) for c in sorted(set(antes) | set(despues))]
        contexto["registros"] = registros
        return contexto
