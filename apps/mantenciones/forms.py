"""Formularios de mantenciones."""
from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.core.formularios import CampoFecha, ModeloFormularioBootstrap
from apps.proveedores.models import Proveedor

from .models import EjecucionMantencion, Mantencion


class MantencionForm(ModeloFormularioBootstrap):
    class Meta:
        model = Mantencion
        # Solo lo que llena el usuario. El condominio lo asigna la vista.
        fields = ["nombre", "frecuencia_meses", "proxima_fecha", "proveedor", "dias_anticipacion"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Recarga de extintores"}),
            "proxima_fecha": CampoFecha(),
        }
        help_texts = {
            "nombre": "Cómo se llama la mantención en el calendario.",
            "frecuencia_meses": "Cada cuántos meses se repite. Al registrar una ejecución, la próxima fecha se calcula con este valor.",
            "proxima_fecha": "Cuándo toca hacerla. Puede ser una fecha ya pasada si está atrasada.",
            "proveedor": "Opcional. Quién la realiza.",
            "dias_anticipacion": "Con cuántos días de anticipación pasa a «Por vencer».",
        }

    def __init__(self, *args, condominio, **kwargs):
        """La vista entrega el condominio activo (igual que en ProveedorForm)."""
        super().__init__(*args, **kwargs)
        # Solo proveedores del condominio y activos; al editar se conserva el actual aunque ya esté inactivo.
        # Así nadie puede enlazar el proveedor de otra comunidad manipulando el formulario.
        self.fields["proveedor"].queryset = Proveedor.objects.filter(condominio=condominio).filter(
            Q(activo=True) | Q(pk=self.instance.proveedor_id)
        )
        self.fields["proveedor"].empty_label = "Sin proveedor"


class EjecucionForm(ModeloFormularioBootstrap):
    class Meta:
        model = EjecucionMantencion
        fields = ["fecha", "observacion"]
        widgets = {
            "fecha": CampoFecha(),
            "observacion": forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: Se recargaron 12 extintores."}),
        }
        help_texts = {
            "fecha": "El día en que se hizo. La próxima fecha se cuenta desde aquí.",
            "observacion": "Opcional. Qué se hizo o qué se encontró.",
        }

    def clean_fecha(self):
        """No se registra como hecha una mantención futura: movería la próxima fecha sin que haya ocurrido."""
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser posterior a hoy.")
        return fecha
