"""Validación del certificado de una mantención: JPG, PNG o PDF reales, de hasta 5 MB (Issue #123, RQ-08)."""
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from apps.core.imagenes import MENSAJE_FORMATO, preparar_imagen

TAMANO_MAXIMO = 5 * 1024 * 1024
MENSAJE = "El certificado debe ser un archivo JPG, PNG o PDF de hasta 5 MB."


def preparar_certificado(archivo):
    """
    Devuelve el archivo listo para guardar. Un PDF se reconoce por su cabecera (`%PDF-`), no por la extensión ni
    por el tipo que manda el navegador, y se guarda con nombre al azar. Una imagen pasa por `preparar_imagen`
    (formato real, sin EXIF, nombre al azar). Cualquier otra cosa se rechaza.

    shortcut: del PDF solo se mira la cabecera y el tamaño; no se analiza su contenido. Se entrega siempre como
    descarga (ver CertificadoView), nunca se abre en el sitio. Si se quisiera mostrarlo en línea, escanearlo antes.
    """
    if not archivo or not isinstance(archivo, UploadedFile):
        return archivo
    if archivo.size > TAMANO_MAXIMO:
        raise ValidationError(MENSAJE)
    cabecera = archivo.read(5)
    archivo.seek(0)
    if cabecera == b"%PDF-":
        return ContentFile(archivo.read(), name=f"{uuid.uuid4().hex}.pdf")
    try:
        return preparar_imagen(archivo, tamano_maximo=TAMANO_MAXIMO, lado_maximo=2000)  # 2000 px: acota la memoria
    except ValidationError as error:
        # El mensaje de formato de la imagen dice solo «JPG o PNG»; aquí el PDF también vale.
        if MENSAJE_FORMATO in error.messages:
            raise ValidationError(MENSAJE) from None
        raise
