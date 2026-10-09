"""
Vistas de cuentas: usuarios del condominio y alta por el administrador (Issue #11, RF12).

Iniciar/cerrar sesión y recuperar la contraseña usan las vistas que ya trae
Django (ver urls.py); aquí están solo las propias de CondoHub.

Permisos:
  - Ver los usuarios del condominio y dar de alta usuarios: administrador
  - El rol se asigna SIEMPRE en el condominio activo, donde el administrador
    ya fue verificado por RolRequeridoMixin: no puede dar roles en condominios ajenos.
"""
from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.views.generic import FormView, ListView

from apps.condominios.models import Membresia
from apps.core.permisos import ADMINISTRADOR, RolRequeridoMixin

from .forms import FormularioAltaUsuario, FormularioRecuperarClave
from .models import Usuario


def enviar_invitacion(request, usuario, rol):
    """
    Envía al usuario nuevo el correo con el enlace para definir su contraseña.
    Reutiliza el formulario de "recuperar contraseña" de Django, que genera un
    enlace seguro de un solo uso, pero con un texto de bienvenida propio.
    """
    formulario = FormularioRecuperarClave({"email": usuario.email})
    formulario.is_valid()  # siempre válido: el correo viene de un usuario existente
    formulario.save(
        request=request,
        use_https=request.is_secure(),
        subject_template_name="cuentas/correo_invitacion_asunto.txt",
        email_template_name="cuentas/correo_invitacion.txt",
        extra_email_context={"condominio": request.condominio, "rol": Membresia.Rol(rol).label},
    )


class UsuarioListView(RolRequeridoMixin, ListView):
    """Personas con algún rol activo en el condominio, con sus roles."""

    roles_permitidos = [ADMINISTRADOR]
    template_name = "cuentas/usuarios.html"
    context_object_name = "usuarios"

    def get_queryset(self):
        condominio = self.request.condominio
        roles = Membresia.objects.filter(condominio=condominio, activo=True)
        return (
            Usuario.objects.filter(membresias__in=roles)
            .distinct()
            .prefetch_related(Prefetch("membresias", queryset=roles, to_attr="roles_aqui"))
        )


class UsuarioCreateView(RolRequeridoMixin, FormView):
    """Alta de un usuario con su rol en el condominio activo."""

    roles_permitidos = [ADMINISTRADOR]
    form_class = FormularioAltaUsuario
    template_name = "cuentas/alta_usuario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs

    def form_valid(self, form):
        usuario, creado = form.save()
        rol = Membresia.Rol(form.cleaned_data["rol"]).label
        if creado:
            enviar_invitacion(self.request, usuario, form.cleaned_data["rol"])
            messages.success(
                self.request,
                f"Cuenta creada para {usuario} como {rol}. Le enviamos un correo a {usuario.email} para que defina su contraseña.",
            )
        else:
            messages.info(
                self.request,
                f"{usuario.email} ya tenía cuenta en CondoHub: se le asignó el rol {rol} en este condominio "
                "(sus datos personales no se modificaron).",
            )
        return redirect("cuentas:usuarios")
