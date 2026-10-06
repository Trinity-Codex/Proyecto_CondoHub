"""Incidentes en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Incidente


@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "condominio", "categoria", "estado", "reportado_por", "fecha_reporte")
    list_filter = ("condominio", "estado", "categoria")
    search_fields = ("titulo", "descripcion")
