"""
Validación del RUT chileno.

Formato aceptado: con o sin puntos, con guion y dígito verificador.
Ejemplos válidos: "12.345.678-5", "12345678-5", "11111111-1".

El dígito verificador se calcula con el algoritmo "módulo 11":
  1. Se multiplican los dígitos del número, de derecha a izquierda,
     por la serie 2, 3, 4, 5, 6, 7, 2, 3, ...
  2. Se suman los resultados.
  3. dv = 11 - (suma % 11)   ->  11 se escribe "0" y 10 se escribe "K".
"""
from django.core.exceptions import ValidationError

# Las funciones puras viven en apps/core/formato.py (Issue #77); se reexportan para no romper imports.
from apps.core.formato import RUT_FORMATO, calcular_dv, normalizar_rut

__all__ = ["RUT_FORMATO", "calcular_dv", "normalizar_rut", "validar_rut"]


def validar_rut(rut):
    """Validador para usar en campos de Django: lanza ValidationError si el RUT no es válido."""
    rut = normalizar_rut(rut)
    coincide = RUT_FORMATO.fullmatch(rut)
    if not coincide:
        raise ValidationError("Formato de RUT inválido. Ejemplo: 12.345.678-5", code="rut_formato")
    numero, dv = coincide.groups()
    if calcular_dv(numero) != dv:
        raise ValidationError("El dígito verificador del RUT no es correcto.", code="rut_dv")
