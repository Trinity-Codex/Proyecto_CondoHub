"""Formularios de gastos comunes."""
from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q

from apps.condominios.models import Edificio
from apps.core.campos import MontoField
from apps.core.formato import formatear_monto
from apps.core.formularios import CampoFecha, FormularioBootstrap, ModeloFormularioBootstrap
from apps.proveedores.models import Proveedor

from .models import DIA_VENCIMIENTO, MESES, MONTO_MAXIMO, Egreso, PeriodoGasto, vencimiento_por_defecto


class PeriodoForm(ModeloFormularioBootstrap):
    """
    Abrir (o corregir) un período de gastos: mes, año, % del fondo de reserva, criterio
    de prorrateo, referencia del reglamento y fecha de vencimiento. Las reglas de esos dos
    últimos campos están en PeriodoGasto.clean(), que el formulario ejecuta al validar.
    """

    class Meta:
        model = PeriodoGasto
        fields = [
            "mes", "anio", "porcentaje_fondo_reserva", "criterio_prorrateo", "referencia_reglamento",
            "fecha_vencimiento",
        ]
        widgets = {
            # El mes se elige de una lista con su nombre en vez de escribir un número.
            "mes": forms.Select(choices=[(i, m.capitalize()) for i, m in enumerate(MESES, start=1)]),
            "anio": forms.NumberInput(attrs={"placeholder": "Ej.: 2026"}),
            "porcentaje_fondo_reserva": forms.NumberInput(attrs={"placeholder": "Ej.: 5"}),
            "referencia_reglamento": forms.TextInput(attrs={"placeholder": "Ej.: Art. 12 del reglamento de copropiedad"}),
            "fecha_vencimiento": CampoFecha(),
        }
        labels = {
            "mes": "Mes", "anio": "Año", "porcentaje_fondo_reserva": "% del fondo de reserva",
            "criterio_prorrateo": "Criterio de prorrateo", "referencia_reglamento": "Referencia del reglamento",
            "fecha_vencimiento": "Fecha de vencimiento",
        }
        help_texts = {
            "mes": "Mes al que corresponden los gastos que se cobrarán. Solo puede haber un período por mes.",
            "anio": "Año del período.",
            "porcentaje_fondo_reserva": "Parte del gasto común que se destina al fondo de reserva. Mínimo 5 % (Ley 21.442).",
            "criterio_prorrateo": "Define cómo se reparte el total entre las unidades. Por defecto, según la alícuota; "
            "usa otro solo si el reglamento del condominio lo indica.",
            "referencia_reglamento": "Opcional. Artículo del reglamento de copropiedad que autoriza el criterio; "
            "debes indicarlo si repartes en partes iguales.",
            "fecha_vencimiento": "Opcional. Último día para pagar sin quedar atrasado. "
            f"Si la dejas vacía, vence el día {DIA_VENCIMIENTO} del mes siguiente.",
        }

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominio = condominio
        # Al abrir un período se propone el vencimiento por defecto del mes inicial.
        mes, anio = self.initial.get("mes"), self.initial.get("anio")
        if not self.instance.pk and mes and anio and not self.initial.get("fecha_vencimiento"):
            self.initial["fecha_vencimiento"] = vencimiento_por_defecto(anio, mes)

    def clean(self):
        """
        Un solo período por mes en cada condominio. El modelo tiene esa regla
        (UniqueConstraint), pero Django solo la revisa en el formulario si
        "condominio" es un campo del formulario; aquí lo asigna la vista, así
        que se valida a mano.
        """
        datos = super().clean()
        self._ajustar_vencimiento_propuesto(datos)
        anio, mes = datos.get("anio"), datos.get("mes")
        if anio and mes:
            repetido = PeriodoGasto.objects.filter(condominio=self.condominio, anio=anio, mes=mes)
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise forms.ValidationError(f"Ya existe el período {MESES[mes - 1]} {anio} en este condominio.")
        return datos

    def _ajustar_vencimiento_propuesto(self, datos):
        """
        Si el administrador cambia el mes o el año pero deja la fecha propuesta (la del
        día 10 siguiente al mes inicial), la fecha se vacía para que save() calcule la del
        mes elegido. Una fecha que el administrador escribió a mano no se toca.
        """
        cambio_de_mes = {"mes", "anio"} & set(self.changed_data)
        mes, anio = self.initial.get("mes"), self.initial.get("anio")
        if not cambio_de_mes or "fecha_vencimiento" in self.changed_data or not (mes and anio):
            return
        if datos.get("fecha_vencimiento") == vencimiento_por_defecto(int(anio), int(mes)):
            datos["fecha_vencimiento"] = None


class EgresoForm(ModeloFormularioBootstrap):
    """Registrar o editar un egreso del período."""

    class Meta:
        model = Egreso
        # periodo y creado_por los asigna la vista.
        fields = ["categoria", "descripcion", "monto", "fecha", "proveedor"]
        widgets = {
            "fecha": CampoFecha(),
            "descripcion": forms.TextInput(attrs={"placeholder": "Ej.: Reposición de luminarias del pasillo"}),
        }
        # MontoField acepta «1.250.000»; los validadores del modelo (mínimo 1 y MONTO_MAXIMO) siguen corriendo.
        field_classes = {"monto": MontoField}
        labels = {"categoria": "Categoría", "descripcion": "Descripción", "monto": "Monto", "fecha": "Fecha del documento"}
        help_texts = {
            "categoria": "Agrupa el gasto en el resumen del período.",
            "descripcion": "Qué se pagó. Se muestra en el detalle del período.",
            "monto": "En pesos, con o sin puntos de miles. Se suma al total que se reparte entre las unidades.",
            "fecha": "Fecha de la boleta o factura.",
            "proveedor": "Opcional. Déjalo en «Sin proveedor» para sueldos, cuentas de luz u otros gastos sin proveedor.",
        }

    def __init__(self, *args, condominio, **kwargs):
        super().__init__(*args, **kwargs)
        # REGLA MULTI-CONDOMINIO: solo se ofrecen proveedores de ESTE condominio, y solo
        # los activos (los desactivados ya no se contratan). Como el <select> se arma con
        # este queryset, un proveedor ajeno enviado a mano se rechaza como opción inválida.
        # Al editar, el proveedor que el egreso ya tenía se mantiene aunque ahora esté inactivo.
        visibles = Q(activo=True)
        if self.instance.proveedor_id:
            visibles |= Q(pk=self.instance.proveedor_id)
        self.fields["proveedor"].queryset = Proveedor.objects.filter(condominio=condominio).filter(visibles)
        self.fields["proveedor"].empty_label = "Sin proveedor"
        self.fields["monto"].widget.attrs["placeholder"] = "Ej.: 450.000"
        # El modelo ya valida el máximo, pero su mensaje trae el número sin puntos; este corre antes
        # (validadores del campo) y lo escribe como lo escribe la persona, sin tocar el modelo.
        self.fields["monto"].validators.append(
            MaxValueValidator(MONTO_MAXIMO, message=f"El monto no puede superar ${formatear_monto(MONTO_MAXIMO)}.")
        )


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


class MovimientoFondoForm(FormularioBootstrap):
    """Monto positivo; el sentido del ajuste se elige explícitamente."""

    monto = MontoField(label="Monto", min_value=0, max_value=MONTO_MAXIMO)
    sentido = forms.ChoiceField(label="Sentido del ajuste", choices=[("SUMAR", "Sumar al fondo"), ("RESTAR", "Restar del fondo")])
    fecha = forms.DateField(label="Fecha contable", widget=CampoFecha(), help_text="Fecha del movimiento respaldado.")
    descripcion = forms.CharField(label="Descripción y respaldo", max_length=200,
        help_text="Describe el origen del saldo o el motivo del movimiento. Usa antecedentes verificables.")
    acuerdo = forms.CharField(label="Acuerdo o referencia justificativa", max_length=200,
        help_text="Referencia del acta que autoriza el egreso o documento que justifica el ajuste.")
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.none(), required=False, empty_label="Sin proveedor",
        help_text="Opcional. Proveedor al que se pagó el egreso.")

    def __init__(self, *args, condominio, tipo, **kwargs):
        super().__init__(*args, **kwargs)
        if tipo != "AJUSTE":
            self.fields.pop("sentido")
        if tipo != "EGRESO":
            self.fields.pop("proveedor")
        else:
            self.fields["proveedor"].queryset = Proveedor.objects.filter(condominio=condominio, activo=True)
        if tipo == "INICIAL":
            self.fields["acuerdo"].required = False
            self.fields["acuerdo"].help_text = "Opcional. Referencia adicional; describe el respaldo del saldo inicial arriba."
        else:
            self.fields["monto"].min_value = 1
            self.fields["monto"].validators.append(MinValueValidator(1))
