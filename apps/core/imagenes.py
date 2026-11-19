"""
Imágenes subidas por usuarios: validación y limpieza compartidas (Issue #116, RQ-01).

La usan el logo y la portada del condominio (#116) y la reutilizan las fotos de incidentes y tareas
(RQ-07, #122) y los certificados de mantención (RQ-08, #123). Reglas:

- Solo JPG y PNG **reales**: Pillow abre el archivo y se mira su formato, no la extensión ni el
  `Content-Type` que manda el navegador. SVG, GIF, WebP, PDF, etc. se rechazan (un SVG puede llevar
  JavaScript y abrirse como página).
- Tamaño máximo (por defecto 2 MB) y un tope de píxeles, para que una imagen pequeña en bytes pero
  enorme al descomprimirse («bomba de descompresión») no agote la memoria del servidor.
- La imagen se vuelve a codificar desde sus píxeles: se pierden los metadatos EXIF (ubicación GPS,
  modelo de cámara, fecha) y cualquier contenido extra pegado al archivo.
- El nombre del archivo guardado se genera al azar; el nombre original nunca llega al disco.

Uso en un formulario (ModelForm con un ImageField opcional):

    def clean_logo(self):
        return preparar_imagen(self.cleaned_data.get("logo"), lado_maximo=512)

y en el modelo: `logo = models.ImageField(upload_to=RutaAleatoria("condominios/logos"), blank=True)`.
"""
import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible
from PIL import Image, ImageOps, UnidentifiedImageError

# 2 MB: suficiente para un logo, una portada o una foto de celular comprimida.
TAMANO_MAXIMO = 2 * 1024 * 1024
# 40 megapíxeles: más que cualquier cámara de celular actual; por encima es casi seguro un archivo hostil.
PIXELES_MAXIMOS = 40_000_000
# Formato que informa Pillow → extensión con la que se guarda.
FORMATOS = {"JPEG": "jpg", "PNG": "png"}

MENSAJE_FORMATO = "El archivo debe ser una imagen JPG o PNG."
MENSAJE_DANADA = "No se pudo leer la imagen. Puede estar dañada; pruebe con otro archivo JPG o PNG."


def _megas(bytes_):
    """2097152 → «2 MB»; 1572864 → «1,5 MB» (coma decimal)."""
    megas = bytes_ / (1024 * 1024)
    return f"{megas:.0f} MB" if megas == int(megas) else f"{megas:.1f} MB".replace(".", ",")


def validar_imagen(archivo, tamano_maximo=TAMANO_MAXIMO):
    """
    Comprueba que `archivo` sea un JPG o PNG real dentro de los límites y devuelve su formato
    («JPEG» o «PNG»). Lanza ValidationError con un mensaje para la persona si no lo es.
    No modifica el archivo; deja el puntero al inicio.
    """
    tamano = getattr(archivo, "size", None)
    if tamano is None:
        archivo.seek(0, 2)
        tamano = archivo.tell()
    if tamano > tamano_maximo:
        raise ValidationError(
            f"La imagen pesa más de {_megas(tamano_maximo)}. Reduzca su tamaño o elija otra.",
            code="imagen_pesada",
        )
    archivo.seek(0)
    try:
        with Image.open(archivo) as imagen:
            # Antes de decodificar: Image.open solo lee la cabecera, así que el tamaño sale sin costo.
            ancho, alto = imagen.size
            if ancho * alto > PIXELES_MAXIMOS:
                raise ValidationError(
                    "La imagen tiene demasiados píxeles. Use una de menor resolución.", code="imagen_enorme"
                )
            formato = imagen.format
            if formato not in FORMATOS:
                raise ValidationError(MENSAJE_FORMATO, code="imagen_formato")
            imagen.verify()  # recorre el archivo y detecta datos truncados o corruptos
    except ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError):
        raise ValidationError(MENSAJE_FORMATO, code="imagen_formato") from None
    except Exception:  # noqa: BLE001 — Pillow lanza varios tipos ante archivos dañados
        raise ValidationError(MENSAJE_DANADA, code="imagen_danada") from None
    finally:
        archivo.seek(0)
    return formato


def preparar_imagen(archivo, tamano_maximo=TAMANO_MAXIMO, lado_maximo=None):
    """
    Valida `archivo` y devuelve un ContentFile listo para asignar a un ImageField: la imagen
    vuelta a codificar, sin metadatos, con nombre al azar y, si se indica `lado_maximo`, reducida
    para que ningún lado lo supere (nunca se agranda).

    Devuelve `archivo` sin tocar si no es una subida nueva (None, False al marcar «Quitar», o el
    archivo que el registro ya tenía guardado), para que el clean_<campo> de un ModelForm pueda
    llamarla siempre.
    """
    if not archivo or not isinstance(archivo, UploadedFile):
        return archivo
    formato = validar_imagen(archivo, tamano_maximo)
    try:
        with Image.open(archivo) as original:
            original.load()
            # Respeta la orientación de la foto (EXIF) antes de descartar los metadatos.
            imagen = ImageOps.exif_transpose(original)
    except Exception:  # noqa: BLE001
        raise ValidationError(MENSAJE_DANADA, code="imagen_danada") from None
    finally:
        archivo.seek(0)

    if lado_maximo:
        imagen.thumbnail((lado_maximo, lado_maximo))
    if formato == "JPEG":
        imagen = imagen.convert("RGB")
    elif imagen.mode not in ("RGB", "RGBA", "L", "LA"):
        imagen = imagen.convert("RGBA")
    # Imagen nueva solo con los píxeles: no hereda EXIF, perfiles ni texto incrustado.
    limpia = Image.new(imagen.mode, imagen.size)
    limpia.paste(imagen)

    salida = BytesIO()
    if formato == "JPEG":
        limpia.save(salida, format="JPEG", quality=85, optimize=True)
    else:
        limpia.save(salida, format="PNG", optimize=True)
    return ContentFile(salida.getvalue(), name=f"{uuid.uuid4().hex}.{FORMATOS[formato]}")


@deconstructible
class RutaAleatoria:
    """
    `upload_to` de un ImageField: guarda en `<carpeta>/<32 caracteres al azar>.<jpg|png>`.
    Ignora el nombre que traiga el archivo (salvo su extensión, que ya puso preparar_imagen).
    Es una clase y no una función para que las migraciones puedan serializarla.
    """

    def __init__(self, carpeta):
        self.carpeta = carpeta.strip("/")

    def __call__(self, instancia, nombre):
        extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        extension = extension if extension in FORMATOS.values() else "bin"
        return f"{self.carpeta}/{uuid.uuid4().hex}.{extension}"

    def __eq__(self, otra):
        return isinstance(otra, RutaAleatoria) and otra.carpeta == self.carpeta
