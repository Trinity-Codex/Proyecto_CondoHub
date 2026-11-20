"""
Mantenciones en el panel /admin/ de Django, solo lectura.

Escribir desde aquí se saltaría las reglas de las vistas del calendario: una ejecución con fecha futura, la próxima
fecha sin recalcular y ningún registro de auditoría. Por eso toda alta, cambio y ejecución pasa por esas vistas.
"""
from django.contrib import admin

from .models import EjecucionMantencion, Mantencion


class SoloLecturaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Mantencion)
class MantencionAdmin(SoloLecturaAdmin):
    list_display = ("nombre", "condominio", "frecuencia_meses", "proxima_fecha", "proveedor")
    list_filter = ("condominio",)
    search_fields = ("nombre",)


@admin.register(EjecucionMantencion)
class EjecucionMantencionAdmin(SoloLecturaAdmin):
    list_display = ("mantencion", "fecha", "usuario")
    list_filter = ("mantencion__condominio",)
