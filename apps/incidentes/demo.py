"""Datos demo de incidentes: uno recibido y otro en proceso, en Vista Verde (Issue #62)."""
from apps.incidentes.models import Incidente


def cargar(datos):
    u = datos["usuarios"]
    condominio = datos["vista_verde"]
    Incidente(
        condominio=condominio, reportado_por=u["residente"], unidad=datos["unidades"]["A-101"],
        categoria=Incidente.Categoria.MANTENCION, titulo="Ampolleta quemada en pasillo piso 1",
        descripcion="La luz del pasillo frente al departamento 101 no enciende desde ayer.",
    ).reportar()
    en_proceso = Incidente(
        condominio=condominio, reportado_por=u["residente2"], categoria=Incidente.Categoria.AREAS_COMUNES,
        titulo="Portón de estacionamientos lento", descripcion="El portón demora mucho en abrir.",
    )
    en_proceso.reportar()
    en_proceso.cambiar_estado(Incidente.Estado.EN_PROCESO, "Se solicitó la visita del técnico para el viernes.")
