"""
Permisos por rol y por condominio (RNF02: control de acceso basado en roles).

Regla de oro de CondoHub (multi-condominio): cada usuario trabaja SIEMPRE
dentro de un "condominio activo" (request.condominio, lo pone el middleware)
y solo ve los datos de ese condominio.

Cómo proteger una vista nueva (ver docs/GUIA_NUEVA_FEATURE.md):

    class MiVista(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
        roles_permitidos = [ADMINISTRADOR, COMITE]   # None = cualquier miembro
        model = MiModelo                             # debe tener campo "condominio"
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.condominios.models import Condominio, Membresia

# Atajos para escribir menos en las vistas.
ADMINISTRADOR = Membresia.Rol.ADMINISTRADOR
COMITE = Membresia.Rol.COMITE
RESIDENTE = Membresia.Rol.RESIDENTE
CONSERJE = Membresia.Rol.CONSERJE


def condominios_del_usuario(usuario):
    """Condominios a los que el usuario tiene acceso. El superusuario ve todos."""
    activos = Condominio.objects.filter(activo=True)
    if usuario.is_superuser:
        return activos
    return activos.filter(membresias__usuario=usuario, membresias__activo=True).distinct()


def roles_en(usuario, condominio):
    """Conjunto de roles del usuario en un condominio, ej. {"RESIDENTE", "COMITE"}."""
    if condominio is None or not usuario.is_authenticated:
        return set()
    if usuario.is_superuser:
        return {ADMINISTRADOR}  # el superusuario actúa como administrador en todos
    return set(
        Membresia.objects.filter(usuario=usuario, condominio=condominio, activo=True).values_list("rol", flat=True)
    )


def tiene_rol(request, *roles):
    """True si el usuario tiene alguno de los roles en el condominio activo. Útil dentro de las vistas."""
    return bool(request.roles & set(roles))


class RolRequeridoMixin(LoginRequiredMixin):
    """
    Exige: 1) sesión iniciada (si no, lleva al login),
           2) un condominio activo (si no, muestra la página "sin condominio"),
           3) alguno de los roles_permitidos en ese condominio (si no, error 403).
    Debe ir PRIMERO en la lista de clases de la vista.
    """

    roles_permitidos = None  # None = cualquier miembro del condominio

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # redirige a LOGIN_URL
        if request.condominio is None:
            return redirect("core:sin_condominio")
        if self.roles_permitidos is not None and not tiene_rol(request, *self.roles_permitidos):
            raise PermissionDenied("No tienes permisos para esta sección.")
        return super().dispatch(request, *args, **kwargs)


class CondominioQuerysetMixin:
    """
    Filtra automáticamente los registros por el condominio activo, para que
    nunca se muestren (ni se editen) datos de otra comunidad.

    campo_condominio: ruta hasta el condominio desde el modelo. Ej.:
        Comunicado -> "condominio"
        Reserva    -> "espacio__condominio"
    """

    campo_condominio = "condominio"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.campo_condominio: self.request.condominio})
