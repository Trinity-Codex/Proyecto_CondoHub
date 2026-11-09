"""Formularios de edificios, unidades y residentes (Issue #10, RF01)."""
from django import forms
from django.utils import timezone

from apps.core.formularios import CampoFecha, FormularioBootstrap, ModeloFormularioBootstrap
from apps.cuentas.models import Usuario

from .importacion import MAX_BYTES
from .models import Edificio, Residente, Unidad


class EdificioForm(ModeloFormularioBootstrap):
    class Meta:
        model = Edificio
        # condominio lo asigna la vista (el condominio activo).
        fields = ["nombre", "direccion"]
        labels = {"nombre": "Nombre", "direccion": "Dirección"}
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Torre A"}),
            "direccion": forms.TextInput(attrs={"placeholder": "Ej.: Av. Los Aromos 1234"}),
        }
        help_texts = {
            "nombre": "Así se muestra en las unidades y en los comunicados. No puede repetirse en el condominio.",
            "direccion": "Opcional. Solo si es distinta a la del condominio.",
        }

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio

    def clean_nombre(self):
        """
        No se repiten nombres de edificio en un condominio. El modelo tiene esa
        regla (UniqueConstraint), pero Django solo la revisa en el formulario si
        "condominio" es un campo del formulario; aquí lo asigna la vista.
        """
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Edificio.objects.filter(condominio=self.condominio, nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError(f"Ya existe un edificio llamado «{nombre}» en este condominio.")
        return nombre


class UnidadForm(ModeloFormularioBootstrap):
    class Meta:
        model = Unidad
        fields = ["edificio", "numero", "piso", "tipo", "alicuota"]
        widgets = {
            "numero": forms.TextInput(attrs={"placeholder": "Ej.: 101"}),
            "piso": forms.NumberInput(attrs={"placeholder": "Ej.: 1"}),
            "alicuota": forms.NumberInput(
                attrs={"step": "0.000001", "min": 0, "max": 1, "placeholder": "Ej.: 0.012500"}
            ),
        }
        labels = {
            "edificio": "Edificio", "numero": "Número", "piso": "Piso", "tipo": "Tipo de unidad", "alicuota": "Alícuota",
        }
        help_texts = {
            "edificio": "Edificio del condominio donde está la unidad.",
            "numero": "Como figura en el reglamento o la escritura; se guarda en mayúsculas. "
            "No puede repetirse en el edificio.",
            "piso": "Los subterráneos van con número negativo (Ej.: -1).",
            "tipo": "Departamento, casa, local, estacionamiento o bodega.",
            "alicuota": "Fracción del total de gastos comunes que paga la unidad: con ella se reparte cada período. "
            "Ej.: 0.012500 equivale a 1,25 %.",
        }

    def __init__(self, *args, condominio, **kwargs):
        """Solo se puede elegir un edificio del condominio activo."""
        super().__init__(*args, **kwargs)
        self.fields["edificio"].queryset = Edificio.objects.filter(condominio=condominio)

    def clean_numero(self):
        return self.cleaned_data["numero"].strip().upper()

    def clean(self):
        """
        No se repiten números en un edificio. Como "edificio" es un campo del
        formulario, Django también lo revisa con la UniqueConstraint, pero aquí
        se compara sin importar mayúsculas y con un mensaje más claro.
        """
        datos = super().clean()
        edificio, numero = datos.get("edificio"), datos.get("numero")
        if edificio and numero:
            repetida = Unidad.objects.filter(edificio=edificio, numero__iexact=numero)
            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)
            if repetida.exists():
                self.add_error("numero", f"Ya existe la unidad {numero} en {edificio.nombre}.")
        return datos

    def validate_unique(self):
        # La unicidad (edificio, número) ya se revisó en clean(); así no sale el error dos veces.
        pass


class ResidenteForm(FormularioBootstrap):
    """Asignar un residente a la unidad buscando su cuenta por correo."""

    correo = forms.EmailField(help_text="Correo con el que la persona inicia sesión en CondoHub.")
    tipo = forms.ChoiceField(choices=Residente.Tipo.choices, initial=Residente.Tipo.PROPIETARIO)
    desde = forms.DateField(
        label="Fecha de inicio",
        widget=CampoFecha(),
        initial=timezone.localdate,
        help_text="Desde cuándo vive en la unidad. Verá los cobros desde ese mes.",
    )

    def __init__(self, *args, unidad, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidad = unidad

    def clean_correo(self):
        correo = self.cleaned_data["correo"]
        usuario = Usuario.objects.filter(email__iexact=correo, is_active=True).first()
        if usuario is None:
            raise forms.ValidationError("No hay ninguna cuenta con ese correo. Primero hay que crear la cuenta.")
        if Residente.objects.filter(usuario=usuario, unidad=self.unidad, activo=True).exists():
            raise forms.ValidationError(f"{usuario} ya es residente de la unidad {self.unidad.numero}.")
        self.cleaned_data["usuario"] = usuario
        return correo

    def clean_desde(self):
        desde = self.cleaned_data["desde"]
        if desde > timezone.localdate():
            raise forms.ValidationError("La fecha de inicio no puede ser futura.")
        return desde

    def save(self):
        """
        Crea el residente, o lo reactiva si antes se había dado de baja en esta
        unidad (la tabla no permite repetir usuario + unidad): la residencia parte
        de la nueva fecha. Residente.save() le da el rol RESIDENTE en el condominio.
        """
        datos = self.cleaned_data
        residente, _ = Residente.objects.get_or_create(
            usuario=datos["usuario"], unidad=self.unidad, defaults={"desde": datos["desde"]}
        )
        residente.tipo = datos["tipo"]
        residente.desde = datos["desde"]
        residente.activo = True
        residente.save()
        return residente


class ImportarForm(FormularioBootstrap):
    """Subir la planilla CSV de unidades y residentes (Issue #13)."""

    archivo = forms.FileField(
        label="Planilla CSV",
        help_text="En Excel: Archivo > Guardar como > CSV. Máximo 1 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > MAX_BYTES:
            raise forms.ValidationError("El archivo pesa más de 1 MB.")
        return archivo
