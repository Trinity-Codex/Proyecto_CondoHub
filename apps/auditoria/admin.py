"""
Admin de auditoría: solo lectura. Un registro no se cambia ni se borra desde el panel,
igual que desde el sitio (ver `RegistroInmutable` en models.py).
"""
from django.contrib import admin

from apps.auditoria.models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("creado", "usuario_nombre", "accion", "objeto_tipo", "objeto_id", "condominio_id")
    list_filter = ("accion", "objeto_tipo")
    search_fields = ("usuario_nombre", "objeto_id")

    def has_add_permission(self, request):
        # Los registros los crea solo `registrar()`, nunca a mano desde el panel.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
