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
    path("", include("apps.core.urls")),
]

# Textos del panel de administración de Django.
admin.site.site_header = "CondoHub · Administración de la plataforma"
admin.site.site_title = "CondoHub"
admin.site.index_title = "Datos de la plataforma"
