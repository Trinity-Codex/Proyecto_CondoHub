"""Pagos en el panel /admin/ de Django."""
from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("detalle", "monto", "medio", "fecha", "registrado_por", "anulado")
    list_filter = ("medio", "anulado")
    search_fields = ("detalle__unidad__numero", "observacion")
    # Solo consulta (#53): crear, editar o borrar un pago aquí se saltaría la validación de saldo,
    # el recálculo del estado del cobro, la auditoría y el aviso al residente. Los pagos se
    # registran con Pago.registrar() y se corrigen con Pago.anular() desde la app.

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
