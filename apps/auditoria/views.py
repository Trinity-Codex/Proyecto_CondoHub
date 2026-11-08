"""
Vistas de auditoria: registro de quién hizo qué y cuándo (Ley 21.719).

Por ahora solo una página provisional (contrato C0, #62). Las vistas reales llegan
con el Issue #27. Solo el administrador: los demás roles reciben 403.
"""
from django.views.generic import TemplateView

from apps.core.permisos import ADMINISTRADOR, CondominioQuerysetMixin, RolRequeridoMixin


class AuditoriaInicioView(RolRequeridoMixin, CondominioQuerysetMixin, TemplateView):
    """Página provisional. CondominioQuerysetMixin queda listo para cuando la app tenga modelo."""

    roles_permitidos = [ADMINISTRADOR]
    template_name = "auditoria/provisional.html"
