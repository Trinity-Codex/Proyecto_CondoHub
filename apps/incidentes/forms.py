"""Formularios de incidentes."""
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from apps.condominios.models import Unidad
from apps.core.formularios import FormularioBootstrap, ModeloFormularioBootstrap

from .models import Incidente

# Límites de las fotos de respaldo (Issue #122; el cliente debe confirmarlos).
MAX_FOTOS_POR_INCIDENTE = 10
MAX_BYTES_FOTO = 5 * 1024 * 1024
EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png"}
TIPOS_FOTO = {"image/jpeg", "image/png"}
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

    def clean(self, data, initial=None):
        archivos = [a for a in (data if isinstance(data, (list, tuple)) else [data]) if a]
        if not archivos and self.required:
            raise ValidationError(self.error_messages["required"], code="required")
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
        if Path(archivo.name).suffix.lower() not in EXTENSIONES_FOTO:
            raise ValidationError("solo se aceptan imágenes JPG o PNG.")
        # El tamaño se mira primero: no tiene sentido abrir con Pillow un archivo que ya se pasó del límite.
        if archivo.size > MAX_BYTES_FOTO:
            raise ValidationError(
                f"pesa {archivo.size / (1024 * 1024):.1f} MB y el máximo es {MAX_BYTES_FOTO // (1024 * 1024)} MB."
            )
        try:
            archivo = super().clean(archivo)  # Pillow abre el contenido y fija archivo.content_type
        except ValidationError:
            raise ValidationError("no es una imagen JPG o PNG válida.") from None
        if archivo.content_type not in TIPOS_FOTO:
            raise ValidationError("solo se aceptan imágenes JPG o PNG.")
        # TODO(#116): validar con apps.core.imagenes cuando esté unido (quita EXIF)
        return archivo


class FotosFormMixin:
    """Añade el límite de fotos por incidente: `existentes` son las que el incidente ya tiene."""

    def __init__(self, *args, existentes=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.existentes = existentes

    def clean_fotos(self):
        fotos = self.cleaned_data["fotos"]
        if self.existentes + len(fotos) > MAX_FOTOS_POR_INCIDENTE:
            raise ValidationError(
                f"Cada incidente admite hasta {MAX_FOTOS_POR_INCIDENTE} fotos: este ya tiene {self.existentes} "
                f"y quieres agregar {len(fotos)}."
            )
        return fotos


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
