"""Formularios de comunicados."""
from django import forms

from apps.condominios.models import Edificio
from apps.core.formularios import ModeloFormularioBootstrap

from .models import Comunicado


class ComunicadoForm(ModeloFormularioBootstrap):
    class Meta:
        model = Comunicado
        # Solo los campos que llena el usuario. condominio y autor los pone la vista.
        fields = ["titulo", "contenido", "tipo", "edificio", "fijado"]
        widgets = {"contenido": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, condominio, **kwargs):
        """La vista entrega el condominio activo: la lista de edificios muestra solo los suyos."""
        super().__init__(*args, **kwargs)
        self.fields["edificio"].queryset = Edificio.objects.filter(condominio=condominio)
        self.fields["edificio"].help_text = "Solo si el comunicado es para un edificio."

    def clean(self):
        """Validación que involucra dos campos: tipo y edificio deben ser coherentes."""
        datos = super().clean()
        tipo, edificio = datos.get("tipo"), datos.get("edificio")
        if tipo == Comunicado.Tipo.POR_EDIFICIO and not edificio:
            self.add_error("edificio", "Elige el edificio al que va dirigido.")
        if tipo == Comunicado.Tipo.GENERAL:
            datos["edificio"] = None  # un comunicado general no lleva edificio
        return datos
