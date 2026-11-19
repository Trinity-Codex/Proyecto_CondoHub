"""
Solo lectura de la demo visual en Render (Issue #111).

Se activa únicamente desde config/settings_render_demo.py; el entorno habitual no lo carga.
Decide en process_view, con la ruta ya resuelta y DESPUÉS de CsrfViewMiddleware (va al final
de MIDDLEWARE), así que un POST permitido conserva su verificación CSRF y las validaciones de
su vista. No basta con ocultar botones: una solicitud directa también se rechaza aquí.
"""
from django.http import HttpResponseForbidden
from django.template import engines

# Métodos que no escriben por definición HTTP. Cualquier otro (POST, PUT, PATCH, DELETE,
# TRACE...) se trata como escritura.
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}

# Únicos POST de la demo: entrar, salir, cambiar de condominio y confirmar un aviso prioritario.
# Los tres primeros solo escriben la sesión y last_login; la vista conserva sus validaciones
# (credenciales, pertenencia al condominio).
POST_PERMITIDOS = {
    "cuentas:iniciar_sesion",
    "cuentas:cerrar_sesion",
    "core:cambiar_condominio",
    # Aviso prioritario (#118): sin confirmarlo, el residente de la demo quedaría bloqueado en él.
    # Solo guarda la lectura del propio residente (LecturaComunicado).
    "comunicados:confirmar_aviso",
    # Mantenciones (#123): la demo deja probar el alta, la edición y el registro de ejecuciones.
    "mantenciones:nueva",
    "mantenciones:editar",
    "mantenciones:ejecucion",
}

# GET que hoy escriben datos de negocio. Revisión del Issue #111: abrir una notificación
# guarda leida=True. Los demás GET (listados, detalles, filtros, CSV, PDF) solo leen.
GET_CON_ESCRITURA = {"notificaciones:abrir"}

# Página propia sin plantilla nueva: extiende base.html, así conserva el menú y el aviso.
PAGINA_BLOQUEO = """{% extends "base.html" %}
{% block titulo %}Acción no disponible en la demo{% endblock %}
{% block contenido %}
<div class="alert alert-warning" role="alert">
  <h1 class="h5"><i class="bi bi-lock" aria-hidden="true"></i> Acción no disponible en la demo</h1>
  <p class="mb-0">Esta es una demo de solo lectura con datos ficticios: puedes recorrer las
  pantallas, pero no se guardan cambios.</p>
</div>
{% if user.is_authenticated %}
<a class="btn btn-primary" href="{% url 'core:inicio' %}">Volver al inicio</a>
{% else %}
<a class="btn btn-primary" href="{% url 'cuentas:iniciar_sesion' %}">Ir al inicio de sesión</a>
{% endif %}
{% endblock %}"""


def es_escritura_bloqueada(metodo, ruta):
    """True si la demo debe rechazar esa combinación de método y nombre de ruta."""
    if metodo in METODOS_SEGUROS:
        return ruta in GET_CON_ESCRITURA
    return not (metodo == "POST" and ruta in POST_PERMITIDOS)


class SoloLecturaDemoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # base.html lo lee para mostrar el aviso; en el entorno habitual no existe.
        request.demo_solo_lectura = True
        return self.get_response(request)

    def process_view(self, request, vista, args, kwargs):
        # Una ruta sin resolver ya termina en 404 antes de llegar aquí.
        ruta = request.resolver_match.view_name
        if not es_escritura_bloqueada(request.method, ruta):
            return None
        contenido = engines["django"].from_string(PAGINA_BLOQUEO).render(request=request)
        return HttpResponseForbidden(contenido)
