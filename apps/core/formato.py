"""
Formato de datos chilenos: funciones puras, sin Django (Issue #76).

Se usan desde filtros de plantilla, formularios, PDF y pruebas. Incluye las funciones del RUT (Issue #77).
La misma gramática de `normalizar_monto` está replicada en `static/js/formato.js` (`esMontoValido`);
la del RUT, en `rutValido` y `formatearRut`.
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


# --- RUT chileno (Issue #77). `apps.cuentas.validadores` las reexporta: los imports antiguos siguen valiendo.
# Cuerpo de 7 u 8 dígitos, guion y dígito verificador (0-9 o K), ya normalizado.
RUT_FORMATO = re.compile(r"(\d{7,8})-([\dK])")


def normalizar_rut(rut):
    """Quita puntos y espacios y deja la K en mayúscula: " 12.345.678-k " -> "12345678-K"."""
    return rut.replace(".", "").replace(" ", "").upper()


def calcular_dv(numero):
    """Calcula el dígito verificador de la parte numérica del RUT (como texto), con el algoritmo módulo 11."""
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


def formatear_rut(valor):
    """
    RUT con puntos para mostrar: «12345678-5» -> «12.345.678-5». Lo que no es un RUT (otro texto, un RUT
    sin guion, None) se devuelve igual. No comprueba el dígito verificador: mostrar no es validar.
    """
    if not isinstance(valor, str):
        return valor
    coincide = RUT_FORMATO.fullmatch(normalizar_rut(valor))
    if not coincide:
        return valor
    cuerpo, dv = coincide.groups()
    # Se agrupa de a tres desde la derecha, por texto: sin int(), para no perder ceros.
    grupos = []
    while cuerpo:
        grupos.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    return ".".join(grupos) + "-" + dv
