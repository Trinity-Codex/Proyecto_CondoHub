"""Usuarios en el panel /admin/ de Django (solo superusuario de la plataforma)."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import FormularioCrearUsuario, FormularioEditarUsuario
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # UserAdmin de Django espera "username"; aquí se adapta al inicio con correo.
    add_form = FormularioCrearUsuario
    form = FormularioEditarUsuario
    list_display = ("email", "first_name", "last_name", "rut", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "rut")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "rut", "telefono")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "rut", "password1", "password2")}),
    )
