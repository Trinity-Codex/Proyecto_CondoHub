"""Formulario de proveedores."""
from apps.core.formularios import ModeloFormularioBootstrap
from apps.cuentas.validadores import normalizar_rut

from .models import Proveedor


class ProveedorForm(ModeloFormularioBootstrap):
    class Meta:
        model = Proveedor
        # Solo lo que llena el usuario. El condominio lo asigna la vista.
        fields = ["rut", "razon_social", "rubro", "contacto", "telefono", "correo"]

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