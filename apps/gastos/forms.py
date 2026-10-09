"""Formularios de gastos comunes."""
from django import forms

from apps.condominios.models import Edificio
from apps.core.formularios import CampoFecha, FormularioBootstrap, ModeloFormularioBootstrap

from .models import MESES, Egreso, PeriodoGasto


class PeriodoForm(ModeloFormularioBootstrap):
    """Abrir (o corregir) un período de gastos: mes, año, % del fondo de reserva y criterio de prorrateo."""

    class Meta:
        model = PeriodoGasto
        fields = ["mes", "anio", "porcentaje_fondo_reserva", "criterio_prorrateo"]
        # El mes se elige de una lista con su nombre en vez de escribir un número.
        widgets = {"mes": forms.Select(choices=[(i, m.capitalize()) for i, m in enumerate(MESES, start=1)])}

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio

    def clean(self):
        """
        Un solo período por mes en cada condominio. El modelo tiene esa regla
        (UniqueConstraint), pero Django solo la revisa en el formulario si
        "condominio" es un campo del formulario; aquí lo asigna la vista, así
        que se valida a mano.
        """
        datos = super().clean()
        anio, mes = datos.get("anio"), datos.get("mes")
        if anio and mes:
            repetido = PeriodoGasto.objects.filter(condominio=self.condominio, anio=anio, mes=mes)
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise forms.ValidationError(f"Ya existe el período {MESES[mes - 1]} {anio} en este condominio.")
        return datos


class EgresoForm(ModeloFormularioBootstrap):
    """Registrar o editar un egreso del período."""

    class Meta:
        model = Egreso
        # periodo y creado_por los asigna la vista.
        fields = ["categoria", "descripcion", "monto", "fecha"]
        widgets = {
            "fecha": CampoFecha(),
            "monto": forms.NumberInput(attrs={"min": 1, "step": 1, "placeholder": "Ej: 450000"}),
        }
        help_texts = {"monto": "En pesos, sin puntos ni signo $."}


class FiltroReporteForm(FormularioBootstrap):
    """
    Filtros del reporte de morosidad (Issue #5). Se envía por GET, así la URL
    del reporte se puede guardar o compartir con los filtros puestos.

    Solo ofrece períodos EMITIDOS y edificios del condominio activo: si alguien
    escribe en la URL el número de un período de otro condominio, el formulario
    lo rechaza ("opción no válida") y no se muestra nada ajeno.
    """

    periodo = forms.ModelChoiceField(queryset=PeriodoGasto.objects.none(), label="Período", empty_label=None)
    edificio = forms.ModelChoiceField(
        queryset=Edificio.objects.none(), label="Edificio", required=False, empty_label="Todos los edificios"
    )
    solo_deuda = forms.BooleanField(label="Solo unidades con deuda", required=False)

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periodo"].queryset = PeriodoGasto.objects.filter(
            condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO
        )
        self.fields["edificio"].queryset = Edificio.objects.filter(condominio=condominio)
        # Edificio.__str__ incluye el condominio ("Torre A (Vista Verde)"); aquí basta el nombre.
        self.fields["edificio"].label_from_instance = lambda edificio: edificio.nombre
