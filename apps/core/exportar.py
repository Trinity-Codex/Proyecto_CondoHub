"""
Descarga de tablas en CSV para Excel, compartida por el reporte de morosidad y la cartera (Issue #54).

    return respuesta_csv("morosidad-2026-10.csv", ["Unidad", "Saldo"], [["A101", 42000], ["A102", 0]])

Excel en español usa «;» como separador (la coma es el decimal) y necesita el BOM de UTF-8 para leer bien
las tildes. Cada celda pasa por `celda_segura`, así que quien arma las filas no tiene que acordarse de ella.
"""
import csv

from django.http import HttpResponse


def celda_segura(valor):
    """
    Evita la "inyección de fórmulas" en Excel: un texto que empieza con = + - @
    (o con tabulación o retorno de carro, según OWASP) se ejecutaría como
    fórmula al abrir el archivo. Se le antepone un apóstrofo.
    Los números se dejan tal cual para que Excel pueda sumarlos.
    """
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return valor


def porcentaje_csv(valor):
    """Un porcentaje como lo lee Excel en español: coma decimal (56.5 -> «56,5»)."""
    return str(valor).replace(".", ",")


def respuesta_csv(nombre, encabezados, filas):
    """
    HttpResponse con un CSV para descargar: `encabezados` y cada fila de `filas` son listas de celdas.
    `nombre` es el nombre del archivo, sin caracteres especiales (lo arma la vista, no el usuario).
    """
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    respuesta.write("\ufeff")  # BOM: le dice a Excel que el archivo es UTF-8
    escritor = csv.writer(respuesta, delimiter=";")
    escritor.writerow([celda_segura(celda) for celda in encabezados])
    for fila in filas:
        escritor.writerow([celda_segura(celda) for celda in fila])
    return respuesta
