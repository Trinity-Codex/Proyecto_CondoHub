"""Mantenciones en el panel /admin/ de Django."""
from django.contrib import admin

from .models import EjecucionMantencion, Mantencion


@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "condominio", "frecuencia_meses", "proxima_fecha", "proveedor")
    list_filter = ("condominio",)
    search_fields = ("nombre",)


@admin.register(EjecucionMantencion)
class EjecucionMantencionAdmin(admin.ModelAdmin):
    list_display = ("mantencion", "fecha", "usuario")
    list_filter = ("mantencion__condominio",)
