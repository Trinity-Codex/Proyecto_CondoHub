"""
Aviso prioritario a pantalla completa (Issue #118, RQ-03).

Mientras un residente tenga un comunicado prioritario vigente sin confirmar, cualquier página
lo lleva a la pantalla del aviso (comunicados:aviso_prioritario). Es un middleware, no un modal
de JavaScript: también funciona al escribir otra URL directamente.

Reglas:
  - Solo se bloquea a quien es residente y no tiene otro rol en el condominio activo
    (administrador, comité y conserje navegan normal).
  - Siempre disponibles: la pantalla del aviso, su confirmación, cerrar sesión, cambiar de
    condominio y las imágenes del encabezado. Los estáticos no pasan por las vistas.
  - Falla abierta: si la consulta falla por un error, el residente sigue navegando (se registra).

Va en settings.MIDDLEWARE después de CondominioActivoMiddleware, que deja request.condominio
y request.roles.
"""
import logging

from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.permisos import ADMINISTRADOR, COMITE, CONSERJE, RESIDENTE

from .models import Comunicado

registro = logging.getLogger(__name__)

RUTAS_LIBRES = {
    "comunicados:aviso_prioritario",
    "comunicados:confirmar_aviso",
    "cuentas:cerrar_sesion",
    "core:cambiar_condominio",
    "condominios:imagen",
}
# Clave de sesión con la página que el residente pidió: al confirmar el último aviso vuelve a ella.
SIGUIENTE = "aviso_prioritario_siguiente"


def debe_ver_avisos(request):
    """True si el usuario es solo residente en el condominio activo (sin rol de administración)."""
    roles = getattr(request, "roles", set())
    return (
        request.user.is_authenticated
        and getattr(request, "condominio", None) is not None
        and RESIDENTE in roles
        and not roles & {ADMINISTRADOR, COMITE, CONSERJE}
    )


def aviso_pendiente(request):
    """Primer aviso prioritario sin confirmar del residente, o None."""
    return Comunicado.objects.avisos_pendientes(request.user, request.condominio, timezone.localdate()).first()


class AvisoPrioritarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, vista, args, kwargs):
        coincidencia = getattr(request, "resolver_match", None)
        if coincidencia is None or coincidencia.view_name in RUTAS_LIBRES or coincidencia.app_name == "admin":
            return None
        try:
            if not debe_ver_avisos(request) or not aviso_pendiente(request):
                return None
        except Exception:  # noqa: BLE001 — falla abierta: un error no deja al residente fuera del sitio
            registro.exception("No se pudo revisar si hay avisos prioritarios pendientes")
            return None
        destino = request.get_full_path()
        if request.method == "GET" and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
            request.session[SIGUIENTE] = destino
        return redirect("comunicados:aviso_prioritario")
