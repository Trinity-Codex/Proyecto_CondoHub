"""
Middleware del "condominio activo".

Un MIDDLEWARE es código que se ejecuta en CADA petición, antes de la vista.
Este deja disponibles, en todas las vistas:
    request.condominio  -> Condominio que el usuario está viendo (o None)
    request.roles       -> roles del usuario en ese condominio, ej. {"RESIDENTE"}

El condominio elegido se guarda en la sesión ("condominio_id"). Si el usuario
nunca eligió uno, se usa el primero al que tiene acceso. Se cambia desde el
selector del menú (vista core:cambiar_condominio).
"""
from .permisos import condominios_del_usuario, roles_en


class CondominioActivoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.condominio = None
        request.roles = set()

        if request.user.is_authenticated:
            disponibles = condominios_del_usuario(request.user)
            condominio_id = request.session.get("condominio_id")
            condominio = disponibles.filter(pk=condominio_id).first() if condominio_id else None
            if condominio is None:
                # Sin elección previa (o ya no tiene acceso): se toma el primero.
                condominio = disponibles.first()
                request.session["condominio_id"] = condominio.pk if condominio else None
            request.condominio = condominio
            request.roles = roles_en(request.user, condominio)

        return self.get_response(request)
