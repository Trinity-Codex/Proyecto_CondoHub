"""Formularios de reservas y espacios comunes."""
from django import forms

from apps.condominios.models import Unidad
from apps.core.campos import MontoField
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
        labels = {
            "espacio": "Espacio común", "unidad": "Unidad", "fecha": "Fecha",
            "hora_inicio": "Hora de inicio", "hora_fin": "Hora de término",
        }
        help_texts = {
            "espacio": "Solo se ofrecen los espacios disponibles para reservar.",
            "unidad": "La unidad a la que se asocia la reserva.",
            "fecha": "Día en que usarás el espacio.",
            "hora_inicio": "Debe estar dentro del horario del espacio.",
            "hora_fin": "Debe ser posterior a la de inicio y no toparse con otra reserva.",
        }

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
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Quincho"}),
            "descripcion": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Ej.: Quincho techado con parrilla y mesón para 20 personas."}
            ),
            "capacidad": forms.NumberInput(attrs={"placeholder": "Ej.: 20"}),
            "hora_apertura": CampoHora(),
            "hora_cierre": CampoHora(),
        }
        field_classes = {"tarifa": MontoField}
        labels = {
            "nombre": "Nombre", "descripcion": "Descripción", "capacidad": "Capacidad",
            "tarifa": "Tarifa por reserva", "hora_apertura": "Hora de apertura", "hora_cierre": "Hora de cierre",
            "activo": "Disponible para reservar",
        }
        help_texts = {
            "nombre": "Así lo ven los residentes al reservar.",
            "descripcion": "Opcional. Qué incluye el espacio y sus normas de uso.",
            "capacidad": "Número máximo de personas.",
            "tarifa": "Pesos chilenos por reserva; escribe 0 si es gratis.",
            "hora_apertura": "Desde esta hora se puede reservar.",
            "hora_cierre": "Ninguna reserva puede terminar después de esta hora.",
            "activo": "Si la desmarcas, el espacio deja de ofrecerse al reservar; las reservas existentes se mantienen.",
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
