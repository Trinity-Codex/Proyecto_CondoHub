"""Espacios comunes y reservas en el panel /admin/ de Django."""
from django.contrib import admin

from .models import EspacioComun, Reserva


@admin.register(EspacioComun)
class EspacioComunAdmin(admin.ModelAdmin):
    list_display = ("nombre", "condominio", "capacidad", "tarifa", "hora_apertura", "hora_cierre", "activo")
    list_filter = ("condominio", "activo")


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("espacio", "fecha", "hora_inicio", "hora_fin", "unidad", "solicitante", "estado")
    list_filter = ("espacio__condominio", "estado", "fecha")
    date_hierarchy = "fecha"
