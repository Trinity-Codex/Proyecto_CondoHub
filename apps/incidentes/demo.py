"""
Datos demo de incidentes en Vista Verde: uno recibido y otro en proceso (Issue #62).
En la demo del cliente se suma uno resuelto (Issue #98), para mostrar los tres estados,
con sus fotos de respaldo «antes» y «después» ficticias (Issue #122).
"""
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from apps.incidentes.models import FotoIncidente, Incidente


def imagen_ficticia(texto, color):
    """PNG de color sólido con un rótulo: sin personas ni datos reales (se genera con Pillow, sin archivos en el repo)."""
    imagen = Image.new("RGB", (640, 480), color)
    ImageDraw.Draw(imagen).text((40, 40), texto, fill="white", font_size=56)
    salida = BytesIO()
    imagen.save(salida, format="PNG")
    return ContentFile(salida.getvalue(), name=f"{texto.lower()}.png")


def cargar_fotos(incidente, u):
    """
    «Antes» a nombre del residente y «después» a nombre del conserje, como en el uso real.
    Se omite si la subida de fotos está apagada: sin almacenamiento persistente se perderían al reiniciar.
    """
    if not settings.FOTOS_INCIDENTES_HABILITADAS:
        return
    FotoIncidente.subir(incidente, [imagen_ficticia("Antes", "#8a5a44")], FotoIncidente.Etapa.ANTES, u["residente"])
    FotoIncidente.subir(incidente, [imagen_ficticia("Después", "#2f7d5b")], FotoIncidente.Etapa.DESPUES, u["conserje"])


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
    if "fecha_referencia_demo" in datos:
        # Solo en la demo del cliente: la carga normal conserva sus dos incidentes (huella intacta).
        # Pasa por reportar() y por cada cambio de estado, como en el uso real, para que el
        # residente tenga su historial de avisos y la respuesta final.
        resuelto = Incidente(
            condominio=condominio, reportado_por=u["residente"], unidad=datos["unidades"]["A-101"],
            categoria=Incidente.Categoria.ASEO, titulo="Basurero del hall con mal olor",
            descripcion="El basurero del hall de entrada tiene mal olor y atrae moscas.",
        )
        resuelto.reportar()
        resuelto.cambiar_estado(Incidente.Estado.EN_PROCESO, "El equipo de aseo lo revisará hoy.")
        resuelto.cambiar_estado(
            Incidente.Estado.RESUELTO, "Se retiró la basura, se lavó el basurero y se agregó una limpieza semanal."
        )
        cargar_fotos(resuelto, u)
