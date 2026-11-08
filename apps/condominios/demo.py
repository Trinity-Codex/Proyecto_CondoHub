"""
Datos demo de condominios (Issue #62, cargar_demo por app).

Crea "Condominio Vista Verde" (el del Informe 2) y "Edificio Los Aromos", para mostrar
que la plataforma es multi-condominio, con sus edificios, unidades (alícuotas que suman 1),
roles y residentes. Deja en datos:
  - "vista_verde" y "los_aromos": los dos condominios;
  - "unidades": las unidades de Vista Verde por "Torre-número", ej. datos["unidades"]["A-101"].

Fechas de residencia (Issue #46): casi todos viven ahí desde hace años, así ven los
cobros demo de los últimos meses. residente2 (B-102) llegó el mes anterior: no ve el
cobro de hace dos meses, que sí aparece en la cobranza y el reporte de la unidad.
"""
from datetime import date, timedelta
from decimal import Decimal

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


def _crear_vista_verde(u):
    condominio = Condominio.objects.create(
        nombre="Condominio Vista Verde", direccion="Av. Los Pinos 1234", comuna="Maipú"
    )
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
