"""Formularios de las solicitudes del titular (Issue #51)."""
from django import forms

from apps.core.formularios import ModeloFormularioBootstrap

from .models import SolicitudTitular


class SolicitudForm(ModeloFormularioBootstrap):
    class Meta:
        model = SolicitudTitular
        fields = ["tipo", "detalle"]  # usuario y condominio los pone la vista
        widgets = {"detalle": forms.Textarea(attrs={"rows": 5})}


class RespuestaForm(ModeloFormularioBootstrap):
    class Meta:
        model = SolicitudTitular
        fields = ["respuesta"]
        widgets = {"respuesta": forms.Textarea(attrs={"rows": 6})}
        help_texts = {"respuesta": "La persona la verá en su solicitud y recibirá un aviso. Al guardar, se cierra."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["respuesta"].required = True  # cerrar sin responder no sirve a la persona
