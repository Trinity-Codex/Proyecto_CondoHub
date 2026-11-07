"""
Vistas de rendicion: rendición de cuentas mensual a la comunidad (Ley 21.442).

Por ahora solo una página provisional (contrato C0, #62). Las vistas reales llegan
con el Issue #55. Administrador y comité: los demás roles reciben 403.
"""
from django.views.generic import TemplateView

from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin


class RendicionInicioView(RolRequeridoMixin, CondominioQuerysetMixin, TemplateView):
    """Página provisional. CondominioQuerysetMixin queda listo para cuando la app tenga modelo."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    template_name = "rendicion/provisional.html"
