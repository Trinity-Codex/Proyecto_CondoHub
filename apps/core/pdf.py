"""
Documentos PDF de CondoHub (contrato C0, Issue #62).

Un PDF se escribe como cualquier plantilla de Django y se convierte con xhtml2pdf:

    from apps.core.pdf import renderizar_pdf

    def aviso_de_cobro(request, pk):
        cobro = ...
        return renderizar_pdf("pagos/pdf/aviso.html", {"cobro": cobro}, f"aviso-{cobro.pk}")

La plantilla extiende "core/pdf/base.html" (márgenes, logo y pie con la fecha) y llena
los bloques "titulo" y "contenido". xhtml2pdf no entiende flexbox ni grid: se maqueta
con tablas (ver docs/GUIA_NUEVA_FEATURE.md).

Seguridad: las imágenes y el CSS solo se leen de static/ (con los finders de Django).
Una URL externa (http://, https://) se ignora, así una plantilla nunca hace solicitudes
a otros servidores al generar un PDF.
"""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.text import get_valid_filename
from xhtml2pdf import pisa
from xhtml2pdf.config.resources import ResourceAccessPolicy


class ErrorPDF(Exception):
    """La plantilla no se pudo convertir a PDF. Nunca se entrega un PDF a medias."""


def _carpetas_estaticas():
    """Carpetas de static/ del proyecto: las únicas desde donde un PDF lee archivos."""
    return [Path(carpeta).resolve() for carpeta in settings.STATICFILES_DIRS]


def _resolver_estatico(uri, rel):
    """
    link_callback de xhtml2pdf: traduce "/static/img/logo.png" (o lo que entrega
    {% static %}) a la ruta del archivo en el disco. Lo que no es un archivo estático
    se devuelve vacío: xhtml2pdf usa la dirección original y la política de acceso
    (sin red, solo static/) la rechaza.
    """
    prefijo = "/" + settings.STATIC_URL.lstrip("/")
    ruta = str(uri)
    if ruta.startswith(prefijo):
        ruta = ruta[len(prefijo):]
    elif "://" in ruta or ruta.startswith("//"):
        return ""
    encontrado = finders.find(ruta.lstrip("/"))
    return str(Path(encontrado).resolve()) if encontrado else ""


def _politica():
    """Sin red, y lectura local solo dentro de static/."""
    carpetas = _carpetas_estaticas()
    return ResourceAccessPolicy.server(
        base_dir=carpetas[0] if carpetas else None,
        extra_roots=tuple(carpetas[1:]),
        allow_remote=False,
    )


def generar_pdf(plantilla, contexto):
    """Renderiza la plantilla y devuelve los bytes del PDF (útil en pruebas y para adjuntar a un correo)."""
    html = render_to_string(plantilla, contexto)
    salida = BytesIO()
    try:
        estado = pisa.CreatePDF(
            html, dest=salida, encoding="utf-8", link_callback=_resolver_estatico, resource_policy=_politica()
        )
    except Exception as error:  # xhtml2pdf puede fallar con HTML muy roto: se informa como ErrorPDF
        raise ErrorPDF(f"No se pudo generar el PDF de {plantilla}: {error}") from error
    if estado.err:
        raise ErrorPDF(f"No se pudo generar el PDF de {plantilla} ({estado.err} errores).")
    return salida.getvalue()


def renderizar_pdf(plantilla: str, contexto: dict, nombre: str) -> HttpResponse:
    """
    Devuelve un HttpResponse con el PDF de la plantilla, para abrirlo en el navegador.

    - plantilla: ruta de la plantilla de Django, ej. "pagos/pdf/aviso.html".
    - contexto: todo lo que la plantilla usa (se renderiza sin request).
    - nombre: nombre del archivo; si no termina en .pdf se le agrega, y se limpian
      los caracteres que no sirven en un nombre de archivo (como "/").
    Lanza ErrorPDF si la conversión falla.
    """
    contenido = generar_pdf(plantilla, contexto)
    base = nombre[:-4] if nombre.lower().endswith(".pdf") else nombre
    # "/" y "\\" separarían carpetas; los puntos y guiones del borde (como en "../") sobran.
    archivo = get_valid_filename(base.replace("/", "-").replace("\\", "-").strip(" .-")) + ".pdf"
    respuesta = HttpResponse(contenido, content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="{archivo}"'
    return respuesta
