"""
Qué cobros puede ver un residente según su período de residencia (Issue #46, contrato C2).

Regla: un residente ACTIVO ve un cobro si su residencia en ESA unidad se superpone con
el mes del período. Quien llega el 20 de marzo ve el cobro completo de marzo. Quien fue
dado de baja no ve los cobros de esa unidad, para que una deuda que ya no le corresponde
no se sume a la suya.

Es solo para lo que ve el residente. La deuda es de la unidad: la cobranza y el reporte
de morosidad no usan este filtro.

Uso (aviso de cobro #6, comprobante #56, recordatorios #57):

    from apps.condominios.residencias import cobros_visibles

    cobros = cobros_visibles(DetalleGastoComun.objects.filter(...), usuario)

Recibe y devuelve un queryset: se puede seguir encadenando (select_related, order_by...).

Con incluir_bajas=True también cuentan las residencias dadas de baja (dentro de sus
fechas): lo usa "Descargar mis datos" (#51), porque los cobros de su período siguen
siendo datos de la persona aunque ya no viva ahí.
"""
from django.db.models import Exists, OuterRef, Q

from .models import Residente


def cobros_visibles(cobros, usuario, incluir_bajas=False):
    """Deja solo los cobros de períodos dentro de la residencia activa del usuario en esa unidad."""
    anio, mes = OuterRef("periodo__anio"), OuterRef("periodo__mes")
    empezo_a_tiempo = Q(desde__year__lt=anio) | Q(desde__year=anio, desde__month__lte=mes)
    sigue_ese_mes = Q(hasta__isnull=True) | Q(hasta__year__gt=anio) | Q(hasta__year=anio, hasta__month__gte=mes)
    residencias = Residente.objects.filter(empezo_a_tiempo, sigue_ese_mes, usuario=usuario, unidad=OuterRef("unidad"))
    if not incluir_bajas:
        residencias = residencias.filter(activo=True)
    # Exists exige que todo se cumpla en la MISMA residencia y no repite cobros.
    return cobros.filter(Exists(residencias))
