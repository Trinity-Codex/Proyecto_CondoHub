"""
Condominios, edificios, unidades, residentes y roles en el panel /admin/ de Django.

El /admin/ es para el SUPERUSUARIO de la plataforma (da de alta condominios y
administradores). Los administradores de cada condominio trabajan en el sitio.
"""
from django.contrib import admin

from .models import Condominio, Edificio, Membresia, Residente, Unidad


class EdificioInline(admin.TabularInline):
    """Permite agregar edificios desde la ficha del condominio."""

    model = Edificio
    extra = 0


class MembresiaInline(admin.TabularInline):
    model = Membresia
    extra = 0
    autocomplete_fields = ["usuario"]


@admin.register(Condominio)
class CondominioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "comuna", "activo", "creado")
    list_filter = ("activo", "comuna")
    search_fields = ("nombre", "direccion")
    inlines = [EdificioInline, MembresiaInline]


class UnidadInline(admin.TabularInline):
    model = Unidad
    extra = 0


@admin.register(Edificio)
class EdificioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "condominio")
    list_filter = ("condominio",)
    inlines = [UnidadInline]


class ResidenteInline(admin.TabularInline):
    model = Residente
    extra = 0
    autocomplete_fields = ["usuario"]


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "piso", "tipo", "alicuota")
    list_filter = ("edificio__condominio", "edificio", "tipo")
    search_fields = ("numero",)
    inlines = [ResidenteInline]


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "condominio", "rol", "activo")
    list_filter = ("condominio", "rol", "activo")
    autocomplete_fields = ["usuario"]


@admin.register(Residente)
class ResidenteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "unidad", "tipo", "activo")
    list_filter = ("unidad__edificio__condominio", "tipo", "activo")
    autocomplete_fields = ["usuario"]
