"""Formulario de proveedores."""
from django import forms

from apps.core.campos import RutField
from apps.core.formularios import ModeloFormularioBootstrap
from apps.cuentas.validadores import normalizar_rut

from .models import Proveedor


class ProveedorForm(ModeloFormularioBootstrap):
    class Meta:
        model = Proveedor
        # Solo lo que llena el usuario. El condominio lo asigna la vista.
        field_classes = {"rut": RutField}
        fields = ["rut", "razon_social", "rubro", "contacto", "telefono", "correo"]
        widgets = {
            "razon_social": forms.TextInput(attrs={"placeholder": "Ej.: Ascensores del Sur SpA"}),
            "rubro": forms.TextInput(attrs={"placeholder": "Ej.: Mantención de ascensores"}),
            "contacto": forms.TextInput(attrs={"placeholder": "Ej.: Pedro Rojas"}),
            "telefono": forms.TextInput(attrs={"placeholder": "Ej.: +56 9 8765 4321", "inputmode": "tel"}),
            "correo": forms.EmailInput(attrs={"placeholder": "Ej.: contacto@example.com"}),
        }
        labels = {
            "razon_social": "Razón social", "rubro": "Rubro", "contacto": "Persona de contacto",
            "telefono": "Teléfono", "correo": "Correo electrónico",
        }
        help_texts = {
            "rut": "Identifica al proveedor en el condominio: no puede repetirse.",
            "razon_social": "Nombre legal, como aparece en sus facturas.",
            "rubro": "Para ubicarlo en la lista según el servicio que presta.",
            "contacto": "Opcional. A quién llamar cuando se necesite el servicio.",
            "telefono": "Opcional.",
            "correo": "Opcional.",
        }

    def __init__(self, *args, condominio, **kwargs):
        """La vista entrega el condominio activo (igual que en ComunicadoForm)."""
        super().__init__(*args, **kwargs)
        self.condominio = condominio

    def clean_rut(self):
        """
        Valida que el RUT no esté repetido en el condominio.
        Lo hacemos aquí porque "condominio" no es un campo del formulario, y por eso
        Django NO revisa el UniqueConstraint del modelo. Se normaliza primero para que
        "12.345.678-5" y "12345678-5" cuenten como el mismo RUT.
        """
        rut = normalizar_rut(self.cleaned_data["rut"])
        repetido = (
            Proveedor.objects.filter(condominio=self.condominio, rut=rut)
            .exclude(pk=self.instance.pk)  # al editar, no choca consigo mismo
            .exists()
        )
        if repetido:
            raise forms.ValidationError("Ya existe un proveedor con este RUT en el condominio.")
        return rut