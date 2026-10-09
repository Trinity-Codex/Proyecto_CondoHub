"""Formularios de cuentas de usuario."""
import secrets

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserChangeForm,
    UserCreationForm,
)
from django.db import transaction

from apps.condominios.models import Membresia
from apps.core.formularios import BootstrapMixin, FormularioBootstrap, ModeloFormularioBootstrap

from .models import Usuario
from .validadores import normalizar_rut, validar_rut


class FormularioInicioSesion(BootstrapMixin, AuthenticationForm):
    """Formulario de inicio de sesión con el correo como usuario."""

    username = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autofocus": True}))


# Formularios que usa el panel /admin/ de Django para crear y editar usuarios
# (los de Django esperan un campo "username", que nuestro Usuario no tiene).
class FormularioCrearUsuario(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name", "rut")


class FormularioEditarUsuario(UserChangeForm):
    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name", "rut", "telefono")


# --------------------------------------------------------------------------
# Recuperar contraseña (vistas de Django con el estilo de Bootstrap)
# --------------------------------------------------------------------------
class FormularioRecuperarClave(BootstrapMixin, PasswordResetForm):
    """Pide el correo y envía el enlace para definir una contraseña nueva."""


class FormularioNuevaClave(BootstrapMixin, SetPasswordForm):
    """Contraseña nueva (dos veces) al abrir el enlace del correo."""


# --------------------------------------------------------------------------
# Alta de usuarios por el administrador (Issue #11, RF12)
# --------------------------------------------------------------------------
def validar_rut_disponible(rut, usuario=None):
    """
    Un RUT identifica a UNA persona: no puede estar en dos cuentas. Devuelve el
    RUT normalizado o lanza ValidationError si ya lo tiene otro usuario.

    usuario: la cuenta que se está editando (su propio RUT no cuenta como
    repetido). Pensado para reutilizarse en el perfil de usuario (#12).
    """
    rut = normalizar_rut(rut)
    otros = Usuario.objects.filter(rut=rut)
    if usuario is not None:
        otros = otros.exclude(pk=usuario.pk)
    if otros.exists():
        raise forms.ValidationError("Ya existe otra cuenta con ese RUT.")
    return rut


class FormularioAltaUsuario(FormularioBootstrap):
    """
    El administrador registra a una persona y le da un rol en el condominio activo.

    - Si el correo NO tiene cuenta: se crea el usuario y se le envía un correo
      con el enlace para que defina su contraseña.
    - Si el correo YA tiene cuenta (por ejemplo, vive en otro condominio): no se
      duplica; solo se le agrega el rol en este condominio.
    """

    email = forms.EmailField(label="Correo electrónico")
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    rut = forms.CharField(label="RUT", max_length=12, validators=[validar_rut], help_text="Ejemplo: 12.345.678-5")
    rol = forms.ChoiceField(
        choices=Membresia.Rol.choices,
        help_text="Para que un residente quede en su unidad, asígnalo luego desde la página Unidades.",
    )

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio
        self.usuario_existente = None

    def clean_email(self):
        email = Usuario.objects.normalize_email(self.cleaned_data["email"]).lower()
        self.usuario_existente = Usuario.objects.filter(email__iexact=email).first()
        return email

    def clean_rut(self):
        """
        Si se va a crear una cuenta nueva, el RUT no puede ser de otra persona.
        Si el correo ya tenía cuenta, el RUT del formulario no se usa (no se
        modifican sus datos), así que no se valida.
        """
        rut = self.cleaned_data["rut"]
        if self.usuario_existente is not None:
            return rut
        return validar_rut_disponible(rut)

    def clean(self):
        datos = super().clean()
        usuario, rol = self.usuario_existente, datos.get("rol")
        if usuario and rol:
            ya_tiene = Membresia.objects.filter(usuario=usuario, condominio=self.condominio, rol=rol, activo=True)
            if ya_tiene.exists():
                self.add_error("rol", f"{usuario} ya tiene el rol {Membresia.Rol(rol).label} en este condominio.")
        return datos

    @transaction.atomic
    def save(self):
        """Crea (o reutiliza) el usuario y su membresía. Devuelve (usuario, creado)."""
        datos = self.cleaned_data
        usuario = self.usuario_existente
        creado = usuario is None
        if creado:
            # Clave aleatoria que nadie conoce: la persona define la suya con el
            # enlace del correo. No se usa set_unusable_password() porque
            # PasswordResetForm no envía correos a usuarios sin clave utilizable.
            usuario = Usuario.objects.create_user(
                email=datos["email"],
                password=secrets.token_urlsafe(16),
                first_name=datos["first_name"],
                last_name=datos["last_name"],
                rut=datos["rut"],
            )
        membresia, _ = Membresia.objects.get_or_create(usuario=usuario, condominio=self.condominio, rol=datos["rol"])
        if not membresia.activo:
            membresia.activo = True
            membresia.save(update_fields=["activo"])
        return usuario, creado


# --------------------------------------------------------------------------
# Perfil de usuario (Issue #12)
# --------------------------------------------------------------------------
class FormularioPerfil(ModeloFormularioBootstrap):
    """
    Datos que cada persona puede cambiar de sí misma. El correo NO está: es con
    lo que inicia sesión y lo que identifica su cuenta (se muestra, no se edita).
    """

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "rut", "telefono"]
        labels = {"first_name": "Nombre", "last_name": "Apellido"}
        help_texts = {"rut": "Ejemplo: 12.345.678-5", "telefono": "Ejemplo: +56 9 1234 5678"}

    def clean_rut(self):
        """El formato y el dígito verificador los revisa el modelo; aquí, que no sea de otra persona."""
        rut = self.cleaned_data["rut"]
        if not rut:
            return rut
        return validar_rut_disponible(rut, usuario=self.instance)

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        digitos = sum(caracter.isdigit() for caracter in telefono)
        if telefono and (not all(c.isdigit() or c in "+ -()" for c in telefono) or not 8 <= digitos <= 15):
            raise forms.ValidationError("Escribe un teléfono válido, por ejemplo +56 9 1234 5678.")
        return telefono


class FormularioCambiarClave(BootstrapMixin, PasswordChangeForm):
    """Clave actual + clave nueva (dos veces), con el estilo de Bootstrap."""
