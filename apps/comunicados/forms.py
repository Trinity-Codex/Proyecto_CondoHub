"""Formularios de comunicados."""
from django import forms
from django.utils import timezone

from apps.condominios.models import Edificio
from apps.core.formularios import CampoFecha, ModeloFormularioBootstrap

from .models import Comunicado


class ComunicadoForm(ModeloFormularioBootstrap):
    class Meta:
        model = Comunicado
        # Solo los campos que llena el usuario. condominio y autor los pone la vista.
        fields = ["titulo", "contenido", "tipo", "edificio", "fijado", "vigente_hasta"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ej.: Corte de agua el sábado 15"}),
            "contenido": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Ej.: Por trabajos en la matriz, el sábado habrá corte de agua de 9:00 a 14:00."}
            ),
            "vigente_hasta": CampoFecha(),
        }
        labels = {
            "titulo": "Título", "contenido": "Contenido", "tipo": "Dirigido a", "edificio": "Edificio",
            "fijado": "Fijar arriba", "vigente_hasta": "Visible hasta",
        }
        help_texts = {
            "titulo": "Es lo primero que ven los residentes en la lista y en la notificación.",
            "contenido": "El detalle del aviso. Se respetan los saltos de línea.",
            "tipo": "«General» llega a todo el condominio; «Solo un edificio», únicamente a ese edificio.",
            "fijado": "Los fijados aparecen primero en la lista.",
            "vigente_hasta": "Opcional. Desde el día siguiente sale de la lista principal (queda en «Ver vencidos»).",
        }

    def __init__(self, *args, condominio, **kwargs):
        """La vista entrega el condominio activo: la lista de edificios muestra solo los suyos."""
        super().__init__(*args, **kwargs)
        self.fields["edificio"].queryset = Edificio.objects.filter(condominio=condominio)
        self.fields["edificio"].help_text = "Opcional. Solo si el comunicado es para un edificio."

    def clean_vigente_hasta(self):
        """
        No puede ser una fecha pasada (Issue #58). Al editar se acepta la que ya tenía, para
        poder corregir el texto de un comunicado vencido sin cambiar su fecha.
        """
        fecha = self.cleaned_data["vigente_hasta"]
        if fecha and fecha < timezone.localdate() and fecha != self.instance.vigente_hasta:
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        return fecha

    def clean(self):
        """Validación que involucra dos campos: tipo y edificio deben ser coherentes."""
        datos = super().clean()
        tipo, edificio = datos.get("tipo"), datos.get("edificio")
        if tipo == Comunicado.Tipo.POR_EDIFICIO and not edificio:
            self.add_error("edificio", "Elige el edificio al que va dirigido.")
        if tipo == Comunicado.Tipo.GENERAL:
            datos["edificio"] = None  # un comunicado general no lleva edificio
        return datos
