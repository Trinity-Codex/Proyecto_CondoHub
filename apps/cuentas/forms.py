"""Formularios de cuentas de usuario."""
import secrets

from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
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
from apps.core.campos import RutField
from apps.core.formularios import BootstrapMixin, FormularioBootstrap, ModeloFormularioBootstrap

from . import limite_intentos
from .models import Usuario
from .validadores import normalizar_rut


class LimiteIntentosMixin:
    """
    Limita los intentos de cualquier formulario de inicio de sesión (Issue #52).
    Va antes del formulario de Django para envolver su clean(), que comprueba la clave.
    """

    def clean(self):
        correo = limite_intentos.normalizar_correo(self.cleaned_data.get("username"))
        direccion = limite_intentos.direccion_cliente(self.request)
        # Se revisa antes de comprobar la clave: durante el bloqueo, ni la correcta entra.
        if limite_intentos.esta_bloqueado(correo, direccion):
            raise forms.ValidationError(limite_intentos.MENSAJE_BLOQUEO, code="bloqueado")
        try:
            datos = super().clean()
        except forms.ValidationError:
            limite_intentos.registrar_fallo(correo, direccion)
            if limite_intentos.esta_bloqueado(correo, direccion):
                raise forms.ValidationError(limite_intentos.MENSAJE_BLOQUEO, code="bloqueado")
            raise
        # Sin usuario no hubo comprobación (faltaba la clave o el correo es inválido): no cuenta.
        if self.get_user() is not None:
            limite_intentos.limpiar_correo(correo)
        return datos


class FormularioInicioSesion(LimiteIntentosMixin, BootstrapMixin, AuthenticationForm):
    """Formulario de inicio de sesión con el correo como usuario."""

    username = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autofocus": True}))


class FormularioInicioAdmin(LimiteIntentosMixin, AdminAuthenticationForm):
    """Inicio de sesión de /admin/: también comprueba claves, así que lleva el mismo límite."""


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

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        # Quien demostró ser dueño del correo no tiene que esperar a que termine el bloqueo.
        if commit:
            limite_intentos.limpiar_correo(usuario.email)
        return usuario


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

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"placeholder": "Ej.: maria.soto@example.com"}),
        help_text="Recibirá aquí la invitación para crear su contraseña y será con lo que inicie sesión.",
    )
    first_name = forms.CharField(
        label="Nombre", max_length=150, widget=forms.TextInput(attrs={"placeholder": "Ej.: María"}),
        help_text="Así se mostrará en los listados y en los correos de CondoHub.",
    )
    last_name = forms.CharField(
        label="Apellido", max_length=150, widget=forms.TextInput(attrs={"placeholder": "Ej.: Soto"}),
    )
    rut = RutField(label="RUT", help_text="Identifica a la persona: no puede estar en dos cuentas.")
    rol = forms.ChoiceField(
        label="Rol en este condominio",
        choices=Membresia.Rol.choices,
        help_text="Define qué puede hacer en este condominio. Para que un residente quede en su unidad, "
        "asígnalo luego desde la página Unidades.",
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
        # recibir_correos: avisos por correo (Issue #14).
        fields = ["first_name", "last_name", "rut", "telefono", "recibir_correos"]
        labels = {
            "first_name": "Nombre", "last_name": "Apellido", "telefono": "Teléfono",
            "recibir_correos": "Recibir avisos por correo",
        }
        field_classes = {"rut": RutField}
        widgets = {"telefono": forms.TextInput(attrs={"placeholder": "Ej.: +56 9 1234 5678", "inputmode": "tel"})}
        help_texts = {
            "first_name": "Así se mostrará en los listados y en los correos de CondoHub.",
            "rut": "Opcional. Identifica a la persona: no puede estar en dos cuentas.",
            "telefono": "Opcional. La administración lo usa para contactarte si hace falta.",
            "recibir_correos": "Comunicados, incidentes, gastos comunes emitidos y pagos registrados.",
        }

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
