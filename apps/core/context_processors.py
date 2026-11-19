"""
Context processor: variables disponibles en TODAS las plantillas sin tener que
pasarlas desde cada vista. Se activa en settings.py (TEMPLATES -> context_processors).

En las plantillas se puede usar, por ejemplo:
    {% if es_admin %} ... {% endif %}
    {{ condominio_activo.nombre }}
"""
from django.utils import timezone

from apps.cartera.permisos import condominios_de_cartera
from apps.comunicados.models import comunicados_sin_leer
from apps.condominios.models import Membresia

from .permisos import ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE, condominios_del_usuario


def condohub(request):
    if not request.user.is_authenticated:
        return {}
    roles = getattr(request, "roles", set())
    condominio = getattr(request, "condominio", None)
    sin_leer = 0
    comunicados_por_leer = 0
    if condominio is not None:
        sin_leer = request.user.notificaciones.filter(condominio=condominio, leida=False).count()
        # Contador junto a «Comunicados» (#120): solo para el residente, lo que ve y no ha leído.
        if RESIDENTE in roles:
            comunicados_por_leer = comunicados_sin_leer(request.user, condominio, timezone.localdate()).count()
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
        "comunicados_sin_leer": comunicados_por_leer,
        # El menú muestra «Cartera» solo a quien tiene condominios asignados (administrador general) o es superusuario.
        "tiene_cartera": condominios_de_cartera(request.user).exists(),
    }
