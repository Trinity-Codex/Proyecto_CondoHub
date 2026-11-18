"""Períodos y egresos en el panel /admin/ de Django (superusuario de la plataforma)."""
from django.contrib import admin

from .models import DetalleGastoComun, Egreso, ItemCobro, LineaCobro, PeriodoGasto


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

    list_display = ("unidad", "periodo", "monto", "monto_fondo_reserva", "monto_items", "total", "estado")
    list_filter = ("periodo__condominio", "periodo", "estado")
    search_fields = ("unidad__numero",)


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "categoria", "monto", "fecha", "periodo")
    list_filter = ("periodo__condominio", "categoria")
    search_fields = ("descripcion",)


@admin.register(ItemCobro)
class ItemCobroAdmin(admin.ModelAdmin):
    """
    Ítems de cobro (#117), solo para consultar. Se crean, editan y eliminan desde la app, que
    bloquea el período, revisa que siga abierto y deja el registro de auditoría.
    """

    list_display = ("nombre", "modo", "monto", "alcance", "periodo")
    list_filter = ("periodo__condominio", "modo", "alcance")
    search_fields = ("nombre",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LineaCobro)
class LineaCobroAdmin(admin.ModelAdmin):
    """Lo que cada ítem le cobró a cada unidad al emitir (solo lectura)."""

    list_display = ("nombre", "monto", "detalle")
    list_filter = ("detalle__periodo__condominio",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
