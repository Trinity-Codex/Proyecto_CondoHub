"""Formularios de mantenciones."""
from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.core.formularios import CampoFecha, ModeloFormularioBootstrap
from apps.proveedores.models import Proveedor

from .certificados import preparar_certificado
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
        if self.instance.pk:
            # Al editar, el formulario lleva oculta la próxima fecha que tenía la mantención al abrirse. Ver clean().
            self.fields["proxima_fecha_cargada"] = forms.DateField(widget=forms.HiddenInput, required=False)
            self.initial["proxima_fecha_cargada"] = self.instance.proxima_fecha

    # @spec:mantenciones-calendario-de-mantenciones
    def clean(self):
        """
        Rechaza el envío de un formulario viejo. Si el administrador abre la edición, registra una ejecución en otra
        pestaña (que recalcula la próxima fecha) y luego envía este formulario, este reenviaría la fecha antigua y
        volvería a dejar vencida una mantención ya hecha. Aquí `self.instance` aún tiene el valor guardado en la base
        (el formulario lo pisa recién después de clean), así que basta compararlo con el que se vio al abrir.
        Es lo más simple que cubre también el caso de abrir el formulario antes de la primera ejecución.

        # ponytail: la comparación y el guardado no son atómicos; la ventana es de milisegundos. Si hiciera falta
        # cerrarla, bloquear la fila con select_for_update dentro de la transacción de la vista.
        """
        datos = super().clean()
        cargada = datos.get("proxima_fecha_cargada")
        if self.instance.pk and cargada != self.instance.proxima_fecha:
            # Solo un formulario viejo (trae la fecha) se redirige; uno armado sin el campo se queda con el error.
            self.desactualizado = cargada is not None
            raise forms.ValidationError(
                "La mantención cambió desde que abriste el formulario (por ejemplo, se registró una ejecución). "
                "Revisa los datos actuales y vuelve a editar."
            )
        return datos


class EjecucionForm(ModeloFormularioBootstrap):
    class Meta:
        model = EjecucionMantencion
        fields = ["fecha", "observacion", "certificado"]
        widgets = {
            "fecha": CampoFecha(),
            "observacion": forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: Se recargaron 12 extintores."}),
        }
        help_texts = {
            "fecha": "El día en que se hizo. La próxima fecha se cuenta desde aquí.",
            "observacion": "Opcional. Qué se hizo o qué se encontró.",
            "certificado": "Opcional. Certificado o foto de respaldo: JPG, PNG o PDF de hasta 5 MB.",
        }

    # @spec:mantenciones-certificados-de-mantencion
    def clean_certificado(self):
        return preparar_certificado(self.cleaned_data.get("certificado"))

    def clean_fecha(self):
        """No se registra como hecha una mantención futura: movería la próxima fecha sin que haya ocurrido."""
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser posterior a hoy.")
        return fecha
