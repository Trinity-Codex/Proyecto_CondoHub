"""Formularios de reservas y espacios comunes."""
from django import forms

from apps.condominios.models import Unidad
from apps.core.formularios import CampoFecha, CampoHora, FormularioBootstrap, ModeloFormularioBootstrap

from .models import EspacioComun, Reserva


class ReservaForm(ModeloFormularioBootstrap):
    """
    RF05: el residente elige espacio, unidad, fecha y horario.
    Las reglas (horario válido, sin topes - RF06) están en Reserva.clean():
    un ModelForm llama a ese método al validar, así que los errores aparecen
    en el formulario sin escribir nada más aquí.
    """

    class Meta:
        model = Reserva
        fields = ["espacio", "unidad", "fecha", "hora_inicio", "hora_fin"]
        widgets = {"fecha": CampoFecha(), "hora_inicio": CampoHora(), "hora_fin": CampoHora()}

    def __init__(self, *args, usuario, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["espacio"].queryset = EspacioComun.objects.filter(condominio=condominio, activo=True)
        mis_unidades = Unidad.objects.filter(
            edificio__condominio=condominio, residentes__usuario=usuario, residentes__activo=True
        ).select_related("edificio")
        self.fields["unidad"].queryset = mis_unidades
        if mis_unidades.count() == 1:
            # Si vive en una sola unidad, se elige sola.
            self.fields["unidad"].initial = mis_unidades.first()


class EspacioComunForm(ModeloFormularioBootstrap):
    """El administrador crea o edita espacios comunes."""

    class Meta:
        model = EspacioComun
        fields = ["nombre", "descripcion", "capacidad", "tarifa", "hora_apertura", "hora_cierre", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "hora_apertura": CampoHora(),
            "hora_cierre": CampoHora(),
        }

    def clean(self):
        datos = super().clean()
        apertura, cierre = datos.get("hora_apertura"), datos.get("hora_cierre")
        if apertura and cierre and cierre <= apertura:
            self.add_error("hora_cierre", "La hora de cierre debe ser posterior a la de apertura.")
        return datos


class FechaForm(FormularioBootstrap):
    """Selector de fecha para consultar la disponibilidad de un espacio (RF05)."""

    fecha = forms.DateField(widget=CampoFecha())
