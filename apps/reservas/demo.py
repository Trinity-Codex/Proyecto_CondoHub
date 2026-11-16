"""
Datos demo de reservas: espacios comunes de los dos condominios y una reserva confirmada (Issue #62).

En la demo del cliente (datos["fecha_referencia_demo"], Issue #96) se suman dos reservas confirmadas
posteriores a esa fecha, en otros espacios y unidades, para que «Próximas reservas» no quede en cero.
La carga normal conserva su única reserva (huella de CargarDemoTest intacta).
"""
from datetime import date, time, timedelta

from apps.reservas.models import EspacioComun, Reserva


def cargar(datos):
    u = datos["usuarios"]
    condominio = datos["vista_verde"]
    quincho = EspacioComun.objects.create(
        condominio=condominio, nombre="Quincho", descripcion="Quincho techado con parrilla y 4 mesas.",
        capacidad=20, tarifa=15000, hora_apertura=time(12), hora_cierre=time(23),
    )
    salon = EspacioComun.objects.create(
        condominio=condominio, nombre="Salón de eventos", descripcion="Salón con cocina, sillas y mesas.",
        capacidad=40, tarifa=25000, hora_apertura=time(10), hora_cierre=time(23),
    )
    gimnasio = EspacioComun.objects.create(
        condominio=condominio, nombre="Gimnasio", descripcion="Máquinas de cardio y pesas.",
        capacidad=8, tarifa=0, hora_apertura=time(6), hora_cierre=time(22),
    )
    EspacioComun.objects.create(condominio=datos["los_aromos"], nombre="Sala multiuso", capacidad=15)

    Reserva(
        espacio=quincho, unidad=datos["unidades"]["A-101"], solicitante=u["residente"],
        fecha=date.today() + timedelta(days=3), hora_inicio=time(13), hora_fin=time(17),
    ).confirmar()

    if "fecha_referencia_demo" in datos:
        # Desde la fecha de la demo o desde hoy, la que sea posterior: las reservas siguen siendo
        # próximas tanto en el ensayo como el día de la reunión (confirmar() rechaza fechas pasadas).
        base = max(datos["fecha_referencia_demo"], date.today())
        Reserva(
            espacio=salon, unidad=datos["unidades"]["B-102"], solicitante=u["residente2"],
            fecha=base + timedelta(days=4), hora_inicio=time(19), hora_fin=time(23),
        ).confirmar()
        Reserva(
            espacio=gimnasio, unidad=datos["unidades"]["A-201"], solicitante=u["comite"],
            fecha=base + timedelta(days=2), hora_inicio=time(7), hora_fin=time(8),
        ).confirmar()
