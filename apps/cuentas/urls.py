"""Rutas de cuentas: iniciar y cerrar sesión (vistas que ya trae Django)."""
from django.contrib.auth import views as vistas_auth
from django.urls import path

from .forms import FormularioInicioSesion

app_name = "cuentas"  # permite referirse a las rutas como "cuentas:iniciar_sesion"

urlpatterns = [
    path(
        "iniciar-sesion/",
        vistas_auth.LoginView.as_view(
            template_name="cuentas/iniciar_sesion.html",
            authentication_form=FormularioInicioSesion,
            redirect_authenticated_user=True,  # si ya inició sesión, va directo al inicio
        ),
        name="iniciar_sesion",
    ),
    # Cerrar sesión exige POST (botón en un formulario), por seguridad.
    path("cerrar-sesion/", vistas_auth.LogoutView.as_view(), name="cerrar_sesion"),
]
