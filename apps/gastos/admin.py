"""Períodos y egresos en el panel /admin/ de Django (superusuario de la plataforma)."""
from django.contrib import admin

from .models import DetalleGastoComun, Egreso, PeriodoGasto


class EgresoInline(admin.TabularInline):
    """Permite ver y editar los egresos desde la ficha del período."""

    model = Egreso
    extra = 0
    autocomplete_fields = ["creado_por"]


@admin.register(PeriodoGasto)
class PeriodoGastoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "condominio", "estado", "porcentaje_fondo_reserva", "total_egresos")
    list_filter = ("condominio", "estado", "anio")
    inlines = [EgresoInline]


@admin.register(DetalleGastoComun)
class DetalleGastoComunAdmin(admin.ModelAdmin):
    """Cobro de cada unidad por período (se crean al emitir el período)."""

    list_display = ("unidad", "periodo", "monto", "monto_fondo_reserva", "total", "estado")
    list_filter = ("periodo__condominio", "periodo", "estado")
    search_fields = ("unidad__numero",)


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "categoria", "monto", "fecha", "periodo")
    list_filter = ("periodo__condominio", "categoria")
    search_fields = ("descripcion",)
