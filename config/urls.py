"""
Rutas principales de CondoHub. Cada app tiene su propio urls.py y aquí se
"anexan" con include(), cada una con su prefijo.

    /                 -> panel de inicio (core)
    /cuentas/         -> iniciar y cerrar sesión
    /condominio/      -> edificios, unidades y residentes
    /comunicados/     -> comunicados oficiales
    /reservas/        -> espacios comunes y reservas
    /incidentes/      -> incidentes
    /notificaciones/  -> notificaciones del usuario
    /gastos/          -> gastos comunes: períodos y egresos
    /proveedores/     -> proveedores del condominio
    /pagos/           -> estado de cuenta, cobranza y pagos
    /auditoria/       -> registro de auditoría (solo administrador)
    /privacidad/      -> aviso de privacidad (público, sin sesión)
    /cartera/         -> cartera de condominios (administrador general y superusuario)
    /rendicion/       -> rendición mensual (administrador y comité)
    /admin/           -> administración de Django (solo superusuario de la plataforma)
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("apps.cuentas.urls")),
    path("condominio/", include("apps.condominios.urls")),
    path("comunicados/", include("apps.comunicados.urls")),
    path("reservas/", include("apps.reservas.urls")),
    path("incidentes/", include("apps.incidentes.urls")),
    path("notificaciones/", include("apps.notificaciones.urls")),
    path("gastos/", include("apps.gastos.urls")),
    path("proveedores/", include("apps.proveedores.urls")),
    path("pagos/", include("apps.pagos.urls")),
    path("auditoria/", include("apps.auditoria.urls")),
    path("privacidad/", include("apps.privacidad.urls")),
    path("cartera/", include("apps.cartera.urls")),
    path("rendicion/", include("apps.rendicion.urls")),
    path("", include("apps.core.urls")),
]

# Textos del panel de administración de Django.
admin.site.site_header = "CondoHub · Administración de la plataforma"
admin.site.site_title = "CondoHub"
admin.site.index_title = "Datos de la plataforma"
