"""Formularios de cuentas de usuario."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from apps.core.formularios import BootstrapMixin

from .models import Usuario


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
