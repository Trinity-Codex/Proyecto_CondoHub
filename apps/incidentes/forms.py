"""Formularios de incidentes."""
import math
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.condominios.models import Unidad
from apps.core.formularios import FormularioBootstrap, ModeloFormularioBootstrap
from apps.core.imagenes import preparar_imagen

from .models import MAX_FOTOS_POR_INCIDENTE, MENSAJE_SIN_MEDIA, Incidente, mensaje_cupo

# Límites de las fotos de respaldo (Issue #122; el cliente debe confirmarlos). El cupo por incidente vive en models.py.
MAX_BYTES_FOTO = 5 * 1024 * 1024
EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png"}
# Extensión con la que se guarda cada formato que Pillow reconoció: así el Content-Type que se sirve
# (se deduce de la extensión) coincide con los bytes y no con el nombre que puso quien subió el archivo.
EXTENSION_POR_FORMATO = {"JPEG": ".jpg", "PNG": ".png"}
AYUDA_FOTOS = f"JPG o PNG, hasta {MAX_BYTES_FOTO // (1024 * 1024)} MB cada una y {MAX_FOTOS_POR_INCIDENTE} por incidente."


class FotosInput(forms.FileInput):
    """Selector de archivos que acepta varias fotos a la vez (Django lo permite con esta marca)."""

    allow_multiple_selected = True


class CampoFotos(forms.ImageField):
    """
    Una o más fotos. Cada archivo debe ser JPG o PNG REAL (Pillow abre el contenido, así que
    un .txt renombrado a .jpg se rechaza) y pesar hasta 5 MB. Devuelve la lista de archivos.
    """

    widget = FotosInput(attrs={"accept": "image/jpeg,image/png"})
    existentes = 0  # fotos que el incidente ya tiene; FotosFormMixin lo fija en la copia de campo de cada formulario

    def clean(self, data, initial=None):
        # @spec:incidentes-fotos-de-respaldo
        archivos = [a for a in (data if isinstance(data, (list, tuple)) else [data]) if a]
        if not archivos and self.required:
            raise ValidationError(self.error_messages["required"], code="required")
        # Primero lo barato: con la subida apagada o sobre el cupo se rechaza sin abrir ningún archivo con Pillow.
        if archivos and not settings.FOTOS_INCIDENTES_HABILITADAS:
            raise ValidationError(MENSAJE_SIN_MEDIA)
        if self.existentes + len(archivos) > MAX_FOTOS_POR_INCIDENTE:
            raise ValidationError(mensaje_cupo(self.existentes, len(archivos)))
        errores = []
        validos = []
        for archivo in archivos:
            try:
                validos.append(self.validar_foto(archivo))
            except ValidationError as error:
                errores.extend(f"«{archivo.name}»: {mensaje}" for mensaje in error.messages)
        if errores:
            raise ValidationError(errores)
        return validos

    def validar_foto(self, archivo):
        # @spec:incidentes-fotos-de-respaldo
        # Las revisiones de extensión y tamaño de abajo no duplican a preparar_imagen: dan mensajes propios de fotos
        # y evitan abrir con Pillow un archivo que ya se sabe inválido.
        if Path(archivo.name).suffix.lower() not in EXTENSIONES_FOTO:
            raise ValidationError("solo se aceptan imágenes JPG o PNG.")
        # El tamaño se mira primero: no tiene sentido abrir con Pillow un archivo que ya se pasó del límite.
        if archivo.size > MAX_BYTES_FOTO:
            # Se redondea hacia ARRIBA: con un decimal normal, un archivo apenas sobre el límite
            # se mostraría como «5.0 MB» y el mensaje parecería contradecirse.
            mb = math.ceil(archivo.size / (1024 * 1024) * 10) / 10
            raise ValidationError(
                f"supera el máximo de {MAX_BYTES_FOTO // (1024 * 1024)} MB (pesa unos {mb:.1f} MB)."
            )
        try:
            archivo = super().clean(archivo)  # Pillow abre el contenido y fija archivo.image
        except ValidationError:
            raise ValidationError("no es una imagen JPG o PNG válida.") from None
        if archivo.image.format not in EXTENSION_POR_FORMATO:
            raise ValidationError("solo se aceptan imágenes JPG o PNG.")
        # Se vuelve a codificar desde los píxeles: sin EXIF (ubicación GPS), con nombre al azar y
        # extensión según el formato real, no según el nombre que mandó el navegador (#116).
        return preparar_imagen(archivo, tamano_maximo=MAX_BYTES_FOTO)


class FotosFormMixin:
    """Avisa del límite de fotos por incidente antes de guardar: `existentes` son las que ya tiene (el servicio lo vuelve a exigir)."""

    def __init__(self, *args, existentes=0, **kwargs):
        super().__init__(*args, **kwargs)
        # Cada formulario tiene su copia del campo, así que fijarlo aquí no afecta a otros formularios.
        self.fields["fotos"].existentes = existentes


class FotosDespuesForm(FotosFormMixin, FormularioBootstrap):
    """La administración o el conserje suben fotos «después» desde el detalle del incidente."""

    fotos = CampoFotos(label="Fotos «después»", help_text=AYUDA_FOTOS)


class IncidenteForm(FotosFormMixin, ModeloFormularioBootstrap):
    """RF07: el residente reporta un incidente, con fotos «antes» opcionales (Issue #122)."""

    fotos = CampoFotos(label="Fotos", required=False, help_text="Opcional. " + AYUDA_FOTOS)

    class Meta:
        model = Incidente
        fields = ["categoria", "titulo", "unidad", "descripcion"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ej.: Luz quemada en el pasillo del piso 3"}),
            "descripcion": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Ej.: Desde el lunes no enciende la luz del pasillo, cerca del ascensor."}
            ),
        }
        labels = {"categoria": "Categoría", "titulo": "Título", "unidad": "Unidad", "descripcion": "Descripción"}
        help_texts = {
            "categoria": "Ayuda a la administración a clasificar el reporte.",
            "titulo": "Resume el problema en pocas palabras.",
            "descripcion": "Cuenta qué ocurre, dónde y desde cuándo, para que la administración pueda resolverlo.",
        }

    def __init__(self, *args, usuario, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo las unidades donde vive el usuario, dentro del condominio activo.
        self.fields["unidad"].queryset = Unidad.objects.filter(
            edificio__condominio=condominio, residentes__usuario=usuario, residentes__activo=True
        )
        self.fields["unidad"].help_text = "Opcional. Déjalo vacío si el incidente es en un área común."


class CambiarEstadoForm(ModeloFormularioBootstrap):
    """RF08: la administración o el conserje cambian el estado y responden."""

    class Meta:
        model = Incidente
        fields = ["estado", "respuesta"]
        widgets = {"respuesta": forms.Textarea(attrs={"rows": 3})}
