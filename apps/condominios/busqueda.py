"""
Búsqueda de unidades y residentes (Issue #82). Una sola regla para el listado de Unidades (`?q=`) y para
las sugerencias en JSON, así nunca pueden diferir.

    unidades = Unidad.objects.filter(edificio__in=<edificios del condominio activo>)
    filtrar_unidades(unidades, "perez 101", ver_rut=ver_rut(request))

Reglas:
  - Cada palabra (hasta 5) debe coincidir (AND) con alguna columna (OR): el número de la unidad, o el
    nombre o apellido de un residente ACTIVO de esa unidad. Un residente dado de baja no cuenta.
  - Solo con `ver_rut` (administrador), una palabra que parece RUT («12.345.678-5», «123456785», «12345»)
    también se compara con el INICIO del RUT, sin puntos ni guion. Al comité el RUT no entra en la
    condición: si filtrara por RUT, que una unidad aparezca o no revelaría el RUT por prueba y error.
  - Mayúsculas y tildes las ignora la collation de MySQL (`utf8mb4_unicode_ci` / `utf8mb4_0900_ai_ci`).
    SQLite solo ignora mayúsculas ASCII; por eso la prueba de tildes corre solo en MySQL.
  - Django escapa `%` y `_` en `icontains`/`istartswith`: el texto escrito nunca es un patrón de LIKE.
"""
import re

from django.db.models import Exists, OuterRef, Q, Value
from django.db.models.functions import Replace

from apps.core.formato import normalizar_rut
from apps.core.listados import normalizar_busqueda
from apps.core.permisos import ADMINISTRADOR, tiene_rol

from .models import Residente

__all__ = ["normalizar_busqueda", "ver_rut", "filtrar_unidades"]

# Una palabra «parece RUT» si, sin puntos ni guion, son solo dígitos con una K final opcional.
_PARECE_RUT = re.compile(r"\d+K?", re.ASCII)


def ver_rut(request):
    """
    Única decisión de si el rol activo puede buscar y ver el RUT de los residentes: solo el administrador
    (el superusuario actúa como tal). Es la misma regla que `es_admin` en la plantilla de Unidades.
    """
    return tiene_rol(request, ADMINISTRADOR)


def _rut_buscable(palabra):
    """«12.345.678-k» -> «12345678K»; None si la palabra no parece un RUT."""
    limpio = normalizar_rut(palabra).replace("-", "")
    return limpio if _PARECE_RUT.fullmatch(limpio) else None


def _coincide(palabra, ver_rut):
    """Condición de una palabra sobre `Unidad`: su número o alguno de sus residentes activos."""
    residentes = Residente.objects.filter(unidad=OuterRef("pk"), activo=True)
    por_residente = Q(usuario__first_name__icontains=palabra) | Q(usuario__last_name__icontains=palabra)
    rut = _rut_buscable(palabra) if ver_rut else None
    if rut:
        residentes = residentes.annotate(rut_sin_guion=Replace("usuario__rut", Value("-"), Value("")))
        por_residente |= Q(rut_sin_guion__istartswith=rut)
    # Exists (y no un join): una unidad con dos residentes no se repite y no hace falta distinct().
    return Q(numero__icontains=palabra) | Q(Exists(residentes.filter(por_residente)))


def filtrar_unidades(unidades, texto, *, ver_rut):
    """
    `unidades` filtradas por `texto` (sin texto, se devuelven igual). `unidades` debe venir ya acotado al
    condominio activo: esta función no agrega ni quita condominios.
    """
    for palabra in normalizar_busqueda(texto).split():
        unidades = unidades.filter(_coincide(palabra, ver_rut))
    return unidades
