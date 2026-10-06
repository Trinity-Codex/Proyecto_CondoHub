"""Comunicados en el panel /admin/ de Django (superusuario de la plataforma)."""
from django.contrib import admin

from .models import Comunicado


@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "condominio", "tipo", "edificio", "fijado", "fecha_publicacion", "autor")
    list_filter = ("condominio", "tipo", "fijado")
    search_fields = ("titulo", "contenido")
