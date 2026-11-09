"""
Admin de cartera: solo el SUPERUSUARIO da o quita el acceso de administrador general (Issue #54, RF20).

Solo hay alta y baja: para cambiar el condominio de una asignación se quita y se asigna otra. Cada alta
y cada baja queda en el registro de auditoría (C1) con `Accion.CAMBIAR_ROL`, en la misma transacción.

Lo que NO se audita: si se borra un usuario o un condominio, Django borra en cascada sus asignaciones
sin pasar por este admin (ni por `registrar()`), así que esas bajas no dejan registro. Son borrados
excepcionales del superusuario; el borrado de un usuario o de un condominio ya es una decisión de mayor peso.
"""
from django.contrib import admin
from django.db import transaction

from .models import AsignacionCartera
from .servicios import registrar_cambio_de_acceso


AVISO_CASCADA = (
    "Si se borra la persona o el condominio, sus accesos se quitan en cascada y ese borrado NO queda en el "
    "registro de auditoría. Para quitar un acceso con registro, bórralo desde aquí."
)


@admin.register(AsignacionCartera)
class AsignacionCarteraAdmin(admin.ModelAdmin):
    list_display = ("usuario", "condominio", "asignada_el")
    list_filter = ("condominio",)
    search_fields = ("usuario__email", "condominio__nombre")
    autocomplete_fields = ["usuario", "condominio"]
    fieldsets = [(None, {"fields": ("usuario", "condominio"), "description": AVISO_CASCADA})]

    # --- permisos: solo el superusuario; sin edición (alta y baja) ---
    def _es_superusuario(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_module_permission(self, request):
        return self._es_superusuario(request)

    def has_view_permission(self, request, obj=None):
        return self._es_superusuario(request)

    def has_add_permission(self, request):
        return self._es_superusuario(request)

    def has_change_permission(self, request, obj=None):
        return False  # al abrir una asignación se ve en solo lectura; para cambiarla se quita y se asigna otra

    def has_delete_permission(self, request, obj=None):
        return self._es_superusuario(request)

    # --- auditoría: el registro y el cambio se guardan juntos o no se guardan ---
    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            registrar_cambio_de_acceso(request.user, obj, asignada=True)

    def delete_model(self, request, obj):
        with transaction.atomic():
            registrar_cambio_de_acceso(request.user, obj, asignada=False)  # antes de borrar: después no hay pk
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """La acción «Eliminar seleccionados»: una línea de auditoría por asignación."""
        with transaction.atomic():
            for asignacion in queryset.select_related("condominio"):
                registrar_cambio_de_acceso(request.user, asignacion, asignada=False)
            super().delete_queryset(request, queryset)
