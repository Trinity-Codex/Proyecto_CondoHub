"""Pagos en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("detalle", "monto", "medio", "fecha", "registrado_por")
    list_filter = ("medio",)
    search_fields = ("detalle__unidad__numero", "observacion")
