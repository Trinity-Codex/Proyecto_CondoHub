"""Datos demo de reservas: espacios comunes de los dos condominios y una reserva confirmada (Issue #62)."""
from datetime import date, time, timedelta

from apps.reservas.models import EspacioComun, Reserva


def cargar(datos):
    u = datos["usuarios"]
    condominio = datos["vista_verde"]
    quincho = EspacioComun.objects.create(
        condominio=condominio, nombre="Quincho", descripcion="Quincho techado con parrilla y 4 mesas.",
        capacidad=20, tarifa=15000, hora_apertura=time(12), hora_cierre=time(23),
    )
    EspacioComun.objects.create(
        condominio=condominio, nombre="Salón de eventos", descripcion="Salón con cocina, sillas y mesas.",
        capacidad=40, tarifa=25000, hora_apertura=time(10), hora_cierre=time(23),
    )
    EspacioComun.objects.create(
        condominio=condominio, nombre="Gimnasio", descripcion="Máquinas de cardio y pesas.",
        capacidad=8, tarifa=0, hora_apertura=time(6), hora_cierre=time(22),
    )
    EspacioComun.objects.create(condominio=datos["los_aromos"], nombre="Sala multiuso", capacidad=15)

    Reserva(
        espacio=quincho, unidad=datos["unidades"]["A-101"], solicitante=u["residente"],
        fecha=date.today() + timedelta(days=3), hora_inicio=time(13), hora_fin=time(17),
    ).confirmar()
