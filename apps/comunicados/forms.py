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
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ej.: Corte de agua el sábado 15"}),
            "contenido": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Ej.: Por trabajos en la matriz, el sábado habrá corte de agua de 9:00 a 14:00."}
            ),
        }
        labels = {
            "titulo": "Título", "contenido": "Contenido", "tipo": "Dirigido a", "edificio": "Edificio",
            "fijado": "Fijar arriba",
        }
        help_texts = {
            "titulo": "Es lo primero que ven los residentes en la lista y en la notificación.",
            "contenido": "El detalle del aviso. Se respetan los saltos de línea.",
            "tipo": "«General» llega a todo el condominio; «Solo un edificio», únicamente a ese edificio.",
            "fijado": "Los fijados aparecen primero en la lista.",
        }

    def __init__(self, *args, condominio, **kwargs):
        """La vista entrega el condominio activo: la lista de edificios muestra solo los suyos."""
        super().__init__(*args, **kwargs)
        self.fields["edificio"].queryset = Edificio.objects.filter(condominio=condominio)
        self.fields["edificio"].help_text = "Opcional. Solo si el comunicado es para un edificio."

    def clean(self):
        """Validación que involucra dos campos: tipo y edificio deben ser coherentes."""
        datos = super().clean()
        tipo, edificio = datos.get("tipo"), datos.get("edificio")
        if tipo == Comunicado.Tipo.POR_EDIFICIO and not edificio:
            self.add_error("edificio", "Elige el edificio al que va dirigido.")
        if tipo == Comunicado.Tipo.GENERAL:
            datos["edificio"] = None  # un comunicado general no lleva edificio
        return datos
