"""
Context processor: variables disponibles en TODAS las plantillas sin tener que
pasarlas desde cada vista. Se activa en settings.py (TEMPLATES -> context_processors).

En las plantillas se puede usar, por ejemplo:
    {% if es_admin %} ... {% endif %}
    {{ condominio_activo.nombre }}
"""
from apps.condominios.models import Membresia

from .permisos import ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE, condominios_del_usuario


def condohub(request):
    if not request.user.is_authenticated:
        return {}
    roles = getattr(request, "roles", set())
    condominio = getattr(request, "condominio", None)
    sin_leer = 0
    if condominio is not None:
        sin_leer = request.user.notificaciones.filter(condominio=condominio, leida=False).count()
    return {
        "condominio_activo": condominio,
        "mis_condominios": condominios_del_usuario(request.user),
        "roles": roles,
        # Nombres legibles de los roles, ej. "Comité de administración, Residente"
        "roles_texto": ", ".join(sorted(Membresia.Rol(r).label for r in roles)),
        "es_admin": ADMINISTRADOR in roles,
        "es_comite": COMITE in roles,
        "es_residente": RESIDENTE in roles,
        "es_conserje": CONSERJE in roles,
        "notificaciones_sin_leer": sin_leer,
    }
