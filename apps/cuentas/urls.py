"""
Rutas de cuentas: iniciar y cerrar sesión, recuperar la contraseña (vistas que
ya trae Django), mi perfil y los usuarios del condominio (vistas propias, en views.py).

Ojo: las vistas de Django buscan por defecto rutas SIN prefijo (por ejemplo
"password_reset_done"), pero las nuestras tienen el prefijo "cuentas:". Por eso
a cada una se le indica su success_url y sus plantillas.
"""
from django.contrib.auth import views as vistas_auth
from django.urls import path, reverse_lazy

from . import views
from .forms import FormularioInicioSesion, FormularioNuevaClave, FormularioRecuperarClave

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
    # --- Recuperar contraseña: 1) pedir el correo  2) "revisa tu correo"
    #     3) enlace del correo -> clave nueva  4) "listo, ya puedes entrar"
    path(
        "recuperar-clave/",
        vistas_auth.PasswordResetView.as_view(
            form_class=FormularioRecuperarClave,
            template_name="cuentas/recuperar_clave.html",
            subject_template_name="cuentas/correo_recuperar_clave_asunto.txt",
            email_template_name="cuentas/correo_recuperar_clave.txt",
            success_url=reverse_lazy("cuentas:recuperar_clave_enviado"),
        ),
        name="recuperar_clave",
    ),
    path(
        "recuperar-clave/enviado/",
        vistas_auth.PasswordResetDoneView.as_view(template_name="cuentas/recuperar_clave_enviado.html"),
        name="recuperar_clave_enviado",
    ),
    path(
        "nueva-clave/<uidb64>/<token>/",
        vistas_auth.PasswordResetConfirmView.as_view(
            form_class=FormularioNuevaClave,
            template_name="cuentas/nueva_clave.html",
            success_url=reverse_lazy("cuentas:nueva_clave_lista"),
        ),
        name="nueva_clave",
    ),
    path(
        "nueva-clave/lista/",
        vistas_auth.PasswordResetCompleteView.as_view(template_name="cuentas/nueva_clave_lista.html"),
        name="nueva_clave_lista",
    ),
    # --- Mi perfil (cualquier usuario con sesión iniciada)
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("perfil/cambiar-clave/", views.CambiarClaveView.as_view(), name="cambiar_clave"),
    # --- Usuarios del condominio (administrador)
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/nuevo/", views.UsuarioCreateView.as_view(), name="usuario_nuevo"),
]
