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
import re

from django.core.exceptions import ValidationError


def normalizar_rut(rut):
    """Quita puntos y espacios y deja la K en mayúscula: " 12.345.678-k " -> "12345678-K"."""
    return rut.replace(".", "").replace(" ", "").upper()


def calcular_dv(numero):
    """Calcula el dígito verificador de la parte numérica del RUT (como texto)."""
    suma = 0
    multiplicador = 2
    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def validar_rut(rut):
    """Validador para usar en campos de Django: lanza ValidationError si el RUT no es válido."""
    rut = normalizar_rut(rut)
    coincide = re.fullmatch(r"(\d{7,8})-([\dK])", rut)
    if not coincide:
        raise ValidationError("Formato de RUT inválido. Ejemplo: 12.345.678-5", code="rut_formato")
    numero, dv = coincide.groups()
    if calcular_dv(numero) != dv:
        raise ValidationError("El dígito verificador del RUT no es correcto.", code="rut_dv")
