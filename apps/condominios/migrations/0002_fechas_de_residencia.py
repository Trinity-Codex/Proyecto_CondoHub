from datetime import date

import django.utils.timezone
from django.db import migrations, models
from django.db.models import F, Q


def fechar_residencias(apps, schema_editor):
    """
    Fecha de inicio de las residencias que ya existen. No hay registro de cuándo se
    crearon, así que se usa lo más antiguo entre la membresía de residente y el primer
    cobro emitido de la unidad: así nadie deja de ver un cobro que ya veía (Issue #46).
    Las filas inactivas quedan sin fecha de término, porque la real se desconoce.
    """
    Residente = apps.get_model("condominios", "Residente")
    Membresia = apps.get_model("condominios", "Membresia")
    DetalleGastoComun = apps.get_model("gastos", "DetalleGastoComun")

    for residente in Residente.objects.select_related("unidad__edificio"):
        candidatas = []
        membresia = (
            Membresia.objects.filter(
                usuario_id=residente.usuario_id, condominio_id=residente.unidad.edificio.condominio_id, rol="RESIDENTE"
            )
            .order_by("desde")
            .first()
        )
        if membresia:
            candidatas.append(membresia.desde)
        primer_periodo = (
            DetalleGastoComun.objects.filter(unidad_id=residente.unidad_id, periodo__estado="EMITIDO")
            .order_by("periodo__anio", "periodo__mes")
            .values_list("periodo__anio", "periodo__mes")
            .first()
        )
        if primer_periodo:
            candidatas.append(date(primer_periodo[0], primer_periodo[1], 1))
        desde = min(candidatas) if candidatas else django.utils.timezone.localdate()
        Residente.objects.filter(pk=residente.pk).update(desde=desde)


class Migration(migrations.Migration):

    dependencies = [
        ("condominios", "0001_initial"),
        ("gastos", "0002_detalle_gasto_comun"),
    ]

    operations = [
        migrations.AddField(
            model_name="residente",
            name="desde",
            field=models.DateField(null=True, verbose_name="fecha de inicio"),
        ),
        migrations.AddField(
            model_name="residente",
            name="hasta",
            field=models.DateField(blank=True, null=True, verbose_name="fecha de término"),
        ),
        migrations.RunPython(fechar_residencias, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="residente",
            name="desde",
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name="fecha de inicio"),
        ),
        migrations.AddConstraint(
            model_name="residente",
            constraint=models.CheckConstraint(
                condition=Q(hasta__isnull=True) | Q(hasta__gte=F("desde")), name="ck_residente_fechas"
            ),
        ),
    ]
