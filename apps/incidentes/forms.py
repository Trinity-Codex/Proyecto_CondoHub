"""Formularios de incidentes."""
from django import forms

from apps.condominios.models import Unidad
from apps.core.formularios import ModeloFormularioBootstrap

from .models import Incidente


class IncidenteForm(ModeloFormularioBootstrap):
    """RF07: el residente reporta un incidente."""

    class Meta:
        model = Incidente
        fields = ["categoria", "titulo", "unidad", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, usuario, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo las unidades donde vive el usuario, dentro del condominio activo.
        self.fields["unidad"].queryset = Unidad.objects.filter(
            edificio__condominio=condominio, residentes__usuario=usuario, residentes__activo=True
        )
        self.fields["unidad"].help_text = "Déjalo vacío si el incidente es en un área común."


class CambiarEstadoForm(ModeloFormularioBootstrap):
    """RF08: la administración o el conserje cambian el estado y responden."""

    class Meta:
        model = Incidente
        fields = ["estado", "respuesta"]
        widgets = {"respuesta": forms.Textarea(attrs={"rows": 3})}
