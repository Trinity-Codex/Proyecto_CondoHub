"""Pagos en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("detalle", "monto", "medio", "fecha", "registrado_por", "anulado")
    list_filter = ("medio", "anulado")
    search_fields = ("detalle__unidad__numero", "observacion")
    # La anulación solo se hace con Pago.anular() (#53): marcarla aquí se saltaría el motivo,
    # la auditoría, el aviso al residente y el recálculo del estado del cobro.
    readonly_fields = ("anulado", "motivo_anulacion", "anulado_en", "anulado_por")
