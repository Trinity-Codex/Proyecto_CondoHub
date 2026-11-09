"""
Formato de datos chilenos: funciones puras, sin Django (Issue #76).

Se usan desde filtros de plantilla, formularios, PDF y pruebas. #77 agregará aquí `formatear_rut`.
La misma gramática de `normalizar_monto` está replicada en `static/js/formato.js` (`esMontoValido`).
"""
import re

# Sin puntos: solo dígitos. Con puntos: el primer grupo no empieza con 0 y los demás son de 3 dígitos.
_MONTO_SIN_PUNTOS = re.compile(r"[0-9]+", re.ASCII)
_MONTO_AGRUPADO = re.compile(r"[1-9][0-9]{0,2}(\.[0-9]{3})+", re.ASCII)


def normalizar_monto(texto):
    """
    Devuelve los dígitos de un monto en pesos escrito por una persona, o None si no es un monto válido.
    Acepta «$ 1.250.000», «1250000» y « 85.000 ». Rechaza decimales («1,5», «1.5», «1500.5»), puntos mal
    agrupados («1.25.000», «0.500»), negativos y letras: en dinero es peor adivinar que preguntar.
    """
    if texto is None:
        return None
    limpio = str(texto).strip()
    if limpio.startswith("$"):
        limpio = limpio[1:].strip()
    if _MONTO_SIN_PUNTOS.fullmatch(limpio):
        return limpio
    if _MONTO_AGRUPADO.fullmatch(limpio):
        return limpio.replace(".", "")
    return None


def formatear_monto(valor):
    """Entero en pesos con punto de miles y sin signo $: 1234567 -> «1.234.567». None -> «0»."""
    if valor is None:
        return "0"
    # f"{1234567:,}" -> "1,234,567"; en Chile el separador de miles es el punto.
    return f"{int(valor):,}".replace(",", ".")
