"""Notificaciones en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "condominio", "leida", "creada")
    list_filter = ("condominio", "leida")
