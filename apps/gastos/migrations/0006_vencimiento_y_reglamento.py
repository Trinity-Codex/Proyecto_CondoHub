"""
Issue #62: fecha de vencimiento y referencia del reglamento en el período.

La fecha de vencimiento es obligatoria, pero ya hay períodos guardados. Por eso
va en tres pasos: 1) se agrega la columna aceptando vacío, 2) cada período existente
recibe el día 10 del mes siguiente a su mes y 3) la columna pasa a ser obligatoria.
"""
from datetime import date

from django.db import migrations, models

# Copia del valor de apps/gastos/models.py al escribir esta migración: una migración
# no debe importar el código actual del modelo, que puede cambiar después.
DIA_VENCIMIENTO = 10


def completar_vencimientos(apps, schema_editor):
    PeriodoGasto = apps.get_model("gastos", "PeriodoGasto")
    for periodo in PeriodoGasto.objects.filter(fecha_vencimiento__isnull=True):
        if periodo.mes == 12:
            periodo.fecha_vencimiento = date(periodo.anio + 1, 1, DIA_VENCIMIENTO)
        else:
            periodo.fecha_vencimiento = date(periodo.anio, periodo.mes + 1, DIA_VENCIMIENTO)
        periodo.save(update_fields=["fecha_vencimiento"])


class Migration(migrations.Migration):

    dependencies = [
        ("gastos", "0005_egreso_proveedor"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodogasto",
            name="referencia_reglamento",
            field=models.CharField(
                blank=True,
                help_text="Artículo del reglamento de copropiedad que autoriza el criterio. Obligatoria si se "
                "reparte en partes iguales. Ej.: Art. 12 del reglamento de copropiedad.",
                max_length=200,
                verbose_name="referencia del reglamento",
            ),
        ),
        migrations.AddField(
            model_name="periodogasto",
            name="fecha_vencimiento",
            field=models.DateField(blank=True, null=True, verbose_name="fecha de vencimiento"),
        ),
        migrations.RunPython(completar_vencimientos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="periodogasto",
            name="fecha_vencimiento",
            field=models.DateField(
                blank=True,
                help_text="Si la dejas vacía, vence el día 10 del mes siguiente.",
                verbose_name="fecha de vencimiento",
            ),
        ),
    ]
