"""Proveedores en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "rubro", "condominio", "activo")
    list_filter = ("condominio", "activo")
    search_fields = ("razon_social", "rut", "rubro")