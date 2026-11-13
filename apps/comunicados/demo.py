"""
Datos demo de comunicados (Issue #62). publicar() también genera las notificaciones (patrón Observer).

Vigencia y lectura (Issue #58), sin agregar comunicados (CargarDemoTest cuenta 3): el corte de
agua de la Torre B ya venció (se ve en «Ver vencidos») y residente2@condohub.cl, que vive en
la Torre B, lo marcó como leído (el administrador ve «1 de N unidades confirmaron»).
"""
from datetime import timedelta

from django.utils import timezone

from apps.comunicados.models import Comunicado, LecturaComunicado


def cargar(datos):
    admin = datos["usuarios"]["administrador"]
    vista_verde = datos["vista_verde"]
    Comunicado(
        condominio=vista_verde, autor=admin, fijado=True,
        titulo="Bienvenidos a CondoHub",
        contenido="Desde hoy los comunicados, reservas de espacios comunes e incidentes se gestionan en esta plataforma.\n\nCualquier duda, escriban a la administración.",
    ).publicar()
    corte = Comunicado(
        condominio=vista_verde, autor=admin, tipo=Comunicado.Tipo.POR_EDIFICIO,
        edificio=vista_verde.edificios.get(nombre="Torre B"),
        titulo="Corte de agua programado en Torre B",
        contenido="El jueves entre las 10:00 y las 14:00 se cortará el agua en la Torre B por mantención de bombas.",
        vigente_hasta=timezone.localdate() - timedelta(days=1),
    )
    corte.publicar()
    LecturaComunicado.objects.create(comunicado=corte, usuario=datos["usuarios"]["residente2"])
    Comunicado(
        condominio=datos["los_aromos"], autor=admin, titulo="Limpieza de estanques",
        contenido="El sábado se realizará la limpieza anual de los estanques de agua.",
    ).publicar()
