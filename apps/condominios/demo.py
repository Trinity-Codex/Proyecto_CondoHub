"""
Datos demo de condominios (Issue #62, cargar_demo por app).

Crea "Condominio Vista Verde" (el del Informe 2) y "Edificio Los Aromos", para mostrar
que la plataforma es multi-condominio, con sus edificios, unidades (alícuotas que suman 1),
roles y residentes. Deja en datos:
  - "vista_verde" y "los_aromos": los dos condominios;
  - "unidades": las unidades de Vista Verde por "Torre-número", ej. datos["unidades"]["A-101"].

Identidad visual (#116): Vista Verde tiene logo y portada ficticios, dibujados aquí con Pillow
(sin archivos binarios en el repositorio); Los Aromos queda sin imágenes para mostrar el
encabezado solo con el nombre.

Fechas de residencia (Issue #46): casi todos viven ahí desde hace años, así ven los
cobros demo de los últimos meses. residente2 (B-102) llegó el mes anterior: no ve el
cobro de hace dos meses, que sí aparece en la cobranza y el reporte de la unidad.
"""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from apps.condominios.models import Condominio, Edificio, Membresia, Residente, Unidad

# cargar_demo --reiniciar borra estos condominios (y en cascada todo lo que cuelga de ellos).
NOMBRES_DEMO = ["Condominio Vista Verde", "Edificio Los Aromos"]

HACE_ANIOS = date(2020, 1, 1)  # residentes de toda la vida: ven todos los cobros demo


def inicio_mes_anterior():
    return (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)


def cargar(datos):
    u = datos["usuarios"]
    datos["vista_verde"], datos["unidades"] = _crear_vista_verde(u)
    datos["los_aromos"] = _crear_los_aromos(u)


def _png(imagen):
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return ContentFile(salida.getvalue())


def logo_demo():
    """Logo ficticio: dos torres blancas y una hoja verde sobre un cuadrado teal redondeado."""
    imagen = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((8, 8, 248, 248), radius=48, fill=(13, 122, 127))
    dibujo.rectangle((62, 92, 118, 206), fill=(255, 255, 255))
    dibujo.rectangle((134, 60, 192, 206), fill=(255, 255, 255))
    for x in (74, 96, 146, 170):
        for y in range(76 if x > 120 else 106, 190, 24):
            dibujo.rectangle((x, y, x + 10, y + 12), fill=(13, 122, 127))
    dibujo.ellipse((150, 160, 214, 214), fill=(129, 188, 70))
    dibujo.rectangle((40, 206, 216, 216), fill=(255, 255, 255))
    return _png(imagen)


def portada_demo():
    """Portada ficticia: cielo degradado, cordillera y edificios en silueta (1600 × 400)."""
    ancho, alto = 1600, 400
    imagen = Image.new("RGB", (ancho, alto))
    dibujo = ImageDraw.Draw(imagen)
    for y in range(alto):  # degradado de celeste a amarillo pálido
        t = y / alto
        dibujo.line([(0, y), (ancho, y)], fill=(int(120 + 120 * t), int(180 + 50 * t), int(225 - 40 * t)))
    dibujo.polygon([(0, 260), (220, 120), (430, 230), (700, 90), (980, 220), (1250, 110), (1600, 240), (1600, 400), (0, 400)],
                   fill=(110, 130, 160))
    dibujo.polygon([(560, 140), (700, 90), (840, 150), (760, 140), (700, 120), (640, 150)], fill=(245, 248, 252))
    for i, (x, h) in enumerate([(120, 170), (300, 230), (520, 190), (980, 240), (1180, 180), (1380, 210)]):
        dibujo.rectangle((x, alto - h, x + 140, alto), fill=(17, 51, 88) if i % 2 else (13, 122, 127))
    dibujo.rectangle((0, alto - 40, ancho, alto), fill=(79, 138, 30))
    return _png(imagen)


def _crear_vista_verde(u):
    condominio = Condominio(nombre="Condominio Vista Verde", direccion="Av. Los Pinos 1234", comuna="Maipú")
    # save=False: un solo INSERT con las dos imágenes ya en el disco (MEDIA_ROOT).
    condominio.logo.save("logo.png", logo_demo(), save=False)
    condominio.portada.save("portada.png", portada_demo(), save=False)
    condominio.save()
    # Alícuotas por torre: 0.12 + 0.08 + 0.12 + 0.08 + 0.10 = 0.50 -> dos torres = 1 (100 %)
    alicuotas = [("101", 1, "0.12"), ("102", 1, "0.08"), ("201", 2, "0.12"), ("202", 2, "0.08"), ("301", 3, "0.10")]
    unidades = {}
    for nombre_torre in ["Torre A", "Torre B"]:
        torre = Edificio.objects.create(condominio=condominio, nombre=nombre_torre)
        for numero, piso, alicuota in alicuotas:
            unidades[f"{nombre_torre[-1]}-{numero}"] = Unidad.objects.create(
                edificio=torre, numero=numero, piso=piso, alicuota=Decimal(alicuota)
            )

    # Roles. Residente.save() agrega solo el rol RESIDENTE (ver condominios/models.py).
    Membresia.objects.create(usuario=u["administrador"], condominio=condominio, rol=Membresia.Rol.ADMINISTRADOR)
    Membresia.objects.create(usuario=u["comite"], condominio=condominio, rol=Membresia.Rol.COMITE)
    Membresia.objects.create(usuario=u["conserje"], condominio=condominio, rol=Membresia.Rol.CONSERJE)
    Residente.objects.create(
        usuario=u["residente"], unidad=unidades["A-101"], tipo=Residente.Tipo.PROPIETARIO, desde=HACE_ANIOS
    )
    Residente.objects.create(
        usuario=u["comite"], unidad=unidades["A-201"], tipo=Residente.Tipo.PROPIETARIO, desde=HACE_ANIOS
    )
    Residente.objects.create(
        usuario=u["residente2"], unidad=unidades["B-102"], tipo=Residente.Tipo.ARRENDATARIO,
        desde=inicio_mes_anterior(),  # recién llegado: no ve el cobro de hace dos meses
    )
    return condominio, unidades


def _crear_los_aromos(u):
    condominio = Condominio.objects.create(nombre="Edificio Los Aromos", direccion="Calle Los Aromos 456", comuna="Ñuñoa")
    edificio = Edificio.objects.create(condominio=condominio, nombre="Edificio único")
    unidades = [
        Unidad.objects.create(edificio=edificio, numero=n, piso=int(n[0]), alicuota=Decimal("0.25"))
        for n in ["101", "102", "201", "202"]
    ]
    # El mismo administrador lleva los dos condominios: verá el selector en el menú.
    Membresia.objects.create(usuario=u["administrador"], condominio=condominio, rol=Membresia.Rol.ADMINISTRADOR)
    Residente.objects.create(
        usuario=u["residente3"], unidad=unidades[0], tipo=Residente.Tipo.PROPIETARIO, desde=HACE_ANIOS
    )
    return condominio
