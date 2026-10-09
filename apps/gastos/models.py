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

Al EMITIR, se crea un DetalleGastoComun por unidad: lo que esa unidad debe pagar
ese mes. Sobre él se construyen el estado de cuenta (#3) y los pagos (#4).

Basado en las tablas "gasto_comun" y "detalle_gasto_comun" del modelo ER del
Informe 2; aquí además se guarda el detalle de cada egreso.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from apps.notificaciones.observador import Sujeto

# Monto máximo de un egreso: 999.999.999 pesos. Evita errores de tipeo con
# demasiados ceros y cabe holgado en la columna de MySQL.
MONTO_MAXIMO = 999_999_999

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


class PeriodoGasto(Sujeto, models.Model):
    """
    Mes de gastos comunes de un condominio.

    Es un "Sujeto" del patrón Observer: al emitirse avisa a los residentes
    (ver apps/notificaciones/observador.py y servicios.emitir_periodo()).
    """

    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EMITIDO = "EMITIDO", "Emitido"

    class Criterio(models.TextChoices):
        """
        Cómo se reparte el total entre las unidades. Cada valor corresponde a una
        estrategia de apps/gastos/prorrateo.py (patrón Strategy).
        """
        ALICUOTA = "ALICUOTA", "Según la alícuota de cada unidad (Ley 21.442)"
        PARTES_IGUALES = "PARTES_IGUALES", "En partes iguales"

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
    criterio_prorrateo = models.CharField(
        "criterio de prorrateo",
        max_length=20,
        choices=Criterio.choices,
        default=Criterio.ALICUOTA,
        help_text="Por defecto, según la alícuota. Usa otro solo si el reglamento del condominio lo indica.",
    )
    fecha_emision = models.DateTimeField("fecha de emisión", null=True, blank=True)
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
    # Proveedor al que se pagó (Issue #9). Es opcional: hay egresos sin proveedor
    # (sueldos, cuentas de luz y agua...). SET_NULL: si un proveedor se eliminara,
    # el egreso se conserva (solo pierde el vínculo), así no se altera el total del período.
    # El comprobante adjunto llega en la fase 2.
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True, related_name="egresos"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="egresos_registrados"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "pk"]

    def __str__(self):
        return f"{self.descripcion} (${self.monto})"


class DetalleGastoComun(models.Model):
    """
    Cobro de gastos comunes de UNA unidad en UN período (tabla "detalle_gasto_comun"
    del Informe 2). Se crea uno por unidad al emitir el período (Issue #2).

    CONTRATO DEL EQUIPO: Winderson construye sobre este modelo el estado de
    cuenta (#3) y los pagos (#4). Sus nombres están acordados en
    docs/equipo/PLAN_DE_TRABAJO.md; si hay que cambiarlos, se conversa antes.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        MOROSO = "MOROSO", "Moroso"

    periodo = models.ForeignKey(PeriodoGasto, on_delete=models.CASCADE, related_name="detalles")
    # RESTRICT (sugerencia de Maximiliano en #34): no se puede borrar una unidad
    # que tiene cobros, para no perder sus deudas ni su historial. A diferencia de
    # PROTECT, sí permite borrar el condominio completo, porque en esa misma
    # operación los cobros se borran a través de su período (cargar_demo --reiniciar).
    unidad = models.ForeignKey("condominios.Unidad", on_delete=models.RESTRICT, related_name="cobros")
    # Parte de los egresos del período que le toca a la unidad (según su alícuota), en pesos.
    monto = models.PositiveIntegerField()
    # Aporte de la unidad al fondo común de reserva (porcentaje del período sobre su monto), en pesos.
    monto_fondo_reserva = models.PositiveIntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)

    class Meta:
        verbose_name = "detalle de gasto común"
        verbose_name_plural = "detalles de gastos comunes"
        ordering = ["periodo", "unidad"]
        constraints = [
            # Una unidad recibe un solo cobro por período.
            models.UniqueConstraint(fields=["periodo", "unidad"], name="uq_detalle_periodo_unidad"),
        ]

    def __str__(self):
        return f"{self.unidad} - {self.periodo}: ${self.total}"

    @property
    def total(self):
        """Lo que la unidad debe pagar en el período (gastos + fondo de reserva)."""
        return self.monto + self.monto_fondo_reserva
