"""
Permisos de la cartera (Issue #54).

La cartera NO usa `RolRequeridoMixin` ni `CondominioQuerysetMixin` (apps/core/permisos.py): el
primero exige un condominio activo y un rol dentro de él, y el administrador general no tiene
ninguno de los dos; el segundo filtra por un solo condominio y la cartera muestra varios.
En su lugar, toda consulta de la app parte de `condominios_de_cartera(request.user)`.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from apps.condominios.models import Condominio


def condominios_de_cartera(usuario):
    """
    Condominios activos que la persona puede consultar en su cartera: los que el superusuario le
    asignó. El superusuario ve todos los activos, como en el resto del sitio.
    """
    activos = Condominio.objects.filter(activo=True)
    if not usuario.is_authenticated:
        return activos.none()
    if usuario.is_superuser:
        return activos
    return activos.filter(asignaciones_cartera__usuario=usuario).distinct()


class CarteraRequeridaMixin(LoginRequiredMixin):
    """
    Exige sesión iniciada (si no, lleva al inicio de sesión) y al menos un condominio en la cartera
    (si no, error 403). Debe ir PRIMERO en la lista de clases de la vista. Deja en `self.condominios`
    los condominios que la persona puede consultar; una vista con `<pk>` busca el suyo ahí con
    `get_object_or_404(self.condominios, pk=pk)`, así uno no asignado da 404.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.condominios = condominios_de_cartera(request.user)
        if not self.condominios.exists():
            raise PermissionDenied("No tienes condominios asignados en la cartera.")
        return super().dispatch(request, *args, **kwargs)
