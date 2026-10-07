"""
Gastos comunes (RF02).

Un PERÍODO es un mes de un condominio (ej. "Octubre 2026"). Durante el mes el
administrador registra los EGRESOS: lo que el condominio gastó (sueldos, luz y
agua de áreas comunes, mantenciones...). Al cerrar el mes, la suma de egresos
se reparte entre las unidades según su alícuota (Issue #2: cálculo y emisión).

Estados del período:
    ABIERTO  -> se pueden agregar, editar y eliminar egresos
    EMITIDO  -> ya se calcularon y cobraron los gastos comunes: los egresos
                quedan bloqueados (cambiarlos descuadraría lo ya cobrado)

Basado en la tabla "gasto_comun" del modelo ER del Informe 2 (que guardaba solo
el monto total); aquí además se guarda el detalle de cada egreso.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

# Monto máximo de un egreso: 999.999.999 pesos. Evita errores de tipeo con
# demasiados ceros y cabe holgado en la columna de MySQL.
MONTO_MAXIMO = 999_999_999

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


class PeriodoGasto(models.Model):
    """Mes de gastos comunes de un condominio."""

    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EMITIDO = "EMITIDO", "Emitido"

    condominio = models.ForeignKey(
        "condominios.Condominio", on_delete=models.CASCADE, related_name="periodos_gasto"
    )
    anio = models.PositiveSmallIntegerField(
        "año", validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    mes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTO)
    # Ley 21.442: el fondo común de reserva no puede ser menor al 5 % de los
    # gastos comunes ordinarios. Se guarda por período por si la asamblea lo cambia.
    porcentaje_fondo_reserva = models.DecimalField(
        "% fondo de reserva",
        max_digits=5,
        decimal_places=2,
        default=Decimal("5"),
        validators=[MinValueValidator(Decimal("5")), MaxValueValidator(Decimal("100"))],
        help_text="Mínimo 5 % (Ley 21.442).",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "período de gastos"
        verbose_name_plural = "períodos de gastos"
        ordering = ["-anio", "-mes"]
        constraints = [
            # Un solo período por mes en cada condominio.
            models.UniqueConstraint(fields=["condominio", "anio", "mes"], name="uq_periodo_mes"),
        ]

    def __str__(self):
        return f"{self.nombre_mes} {self.anio}"

    def get_absolute_url(self):
        return reverse("gastos:periodo_detalle", args=[self.pk])

    @property
    def nombre_mes(self):
        """Nombre del mes con mayúscula inicial: "Octubre"."""
        return MESES[self.mes - 1].capitalize()

    @property
    def esta_abierto(self):
        return self.estado == self.Estado.ABIERTO

    def total_egresos(self):
        """Suma de todos los egresos del período (0 si no hay)."""
        return self.egresos.aggregate(total=models.Sum("monto"))["total"] or 0


class Egreso(models.Model):
    """Gasto del condominio dentro de un período (ej. sueldo del conserje, cuenta de la luz)."""

    class Categoria(models.TextChoices):
        REMUNERACIONES = "REMUNERACIONES", "Remuneraciones"
        CONSUMOS = "CONSUMOS", "Consumos básicos (luz, agua, gas)"
        MANTENCION = "MANTENCION", "Mantención y reparaciones"
        ASEO = "ASEO", "Aseo"
        SEGURIDAD = "SEGURIDAD", "Seguridad"
        ADMINISTRACION = "ADMINISTRACION", "Administración"
        OTROS = "OTROS", "Otros"

    periodo = models.ForeignKey(PeriodoGasto, on_delete=models.CASCADE, related_name="egresos")
    categoria = models.CharField("categoría", max_length=20, choices=Categoria.choices)
    descripcion = models.CharField("descripción", max_length=200)
    # Pesos chilenos: enteros, sin decimales, y al menos $1.
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(MONTO_MAXIMO)])
    fecha = models.DateField(default=date.today, help_text="Fecha de la boleta o factura.")
    # El proveedor se agrega en el Issue #9 (Winderson) y el comprobante adjunto, en la fase 2.
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="egresos_registrados"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.descripcion} (${self.monto})"
