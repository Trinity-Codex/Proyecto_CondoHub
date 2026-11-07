"""Datos demo de comunicados (Issue #62). publicar() también genera las notificaciones (patrón Observer)."""
from apps.comunicados.models import Comunicado


def cargar(datos):
    admin = datos["usuarios"]["administrador"]
    vista_verde = datos["vista_verde"]
    Comunicado(
        condominio=vista_verde, autor=admin, fijado=True,
        titulo="Bienvenidos a CondoHub",
        contenido="Desde hoy los comunicados, reservas de espacios comunes e incidentes se gestionan en esta plataforma.\n\nCualquier duda, escriban a la administración.",
    ).publicar()
    Comunicado(
        condominio=vista_verde, autor=admin, tipo=Comunicado.Tipo.POR_EDIFICIO,
        edificio=vista_verde.edificios.get(nombre="Torre B"),
        titulo="Corte de agua programado en Torre B",
        contenido="El jueves entre las 10:00 y las 14:00 se cortará el agua en la Torre B por mantención de bombas.",
    ).publicar()
    Comunicado(
        condominio=datos["los_aromos"], autor=admin, titulo="Limpieza de estanques",
        contenido="El sábado se realizará la limpieza anual de los estanques de agua.",
    ).publicar()
