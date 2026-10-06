"""
Datos de prueba reutilizables para los tests de todas las apps.

Uso en un test:

    from apps.core.pruebas import crear_escenario

    class MiPrueba(TestCase):
        def setUp(self):
            self.e = crear_escenario()        # condominio, unidades y un usuario por rol
            self.client.force_login(self.e.residente)

El escenario tiene 2 condominios para poder probar que los datos de uno
NUNCA se ven desde el otro (regla multi-condominio).
"""
from datetime import time
from decimal import Decimal
from types import SimpleNamespace

from apps.condominios.models import Condominio, Edificio, Membresia, Residente, Unidad
from apps.cuentas.models import Usuario
from apps.reservas.models import EspacioComun

CLAVE = "clave-de-prueba-123"


def crear_usuario(correo, **campos):
    return Usuario.objects.create_user(email=correo, password=CLAVE, first_name=correo.split("@")[0], **campos)


def crear_escenario():
    """
    Condominio "Prueba" con:
      - Torre A (unidades A101 y A102) y Torre B (unidad B101), alícuotas que suman 1
      - administrador, comite, conserje
      - residente (A101), residente_b (B101)
      - espacio común "Quincho" (09:00 a 22:00)
    Y otro condominio "Ajeno" con su propio residente (residente_ajeno).
    """
    condominio = Condominio.objects.create(nombre="Prueba", direccion="Calle 1", comuna="Santiago")
    torre_a = Edificio.objects.create(condominio=condominio, nombre="Torre A")
    torre_b = Edificio.objects.create(condominio=condominio, nombre="Torre B")
    a101 = Unidad.objects.create(edificio=torre_a, numero="A101", alicuota=Decimal("0.4"))
    a102 = Unidad.objects.create(edificio=torre_a, numero="A102", alicuota=Decimal("0.3"))
    b101 = Unidad.objects.create(edificio=torre_b, numero="B101", alicuota=Decimal("0.3"))

    administrador = crear_usuario("admin@prueba.cl")
    comite = crear_usuario("comite@prueba.cl")
    conserje = crear_usuario("conserje@prueba.cl")
    Membresia.objects.create(usuario=administrador, condominio=condominio, rol=Membresia.Rol.ADMINISTRADOR)
    Membresia.objects.create(usuario=comite, condominio=condominio, rol=Membresia.Rol.COMITE)
    Membresia.objects.create(usuario=conserje, condominio=condominio, rol=Membresia.Rol.CONSERJE)

    residente = crear_usuario("residente@prueba.cl")
    residente_b = crear_usuario("residente.b@prueba.cl")
    Residente.objects.create(usuario=residente, unidad=a101)
    Residente.objects.create(usuario=residente_b, unidad=b101)

    quincho = EspacioComun.objects.create(
        condominio=condominio, nombre="Quincho", capacidad=10, hora_apertura=time(9), hora_cierre=time(22)
    )

    # Otro condominio, para comprobar que sus datos no se mezclan.
    ajeno = Condominio.objects.create(nombre="Ajeno", direccion="Calle 2", comuna="Ñuñoa")
    torre_ajena = Edificio.objects.create(condominio=ajeno, nombre="Torre única")
    unidad_ajena = Unidad.objects.create(edificio=torre_ajena, numero="101", alicuota=Decimal("1"))
    residente_ajeno = crear_usuario("ajeno@prueba.cl")
    Residente.objects.create(usuario=residente_ajeno, unidad=unidad_ajena)

    return SimpleNamespace(**locals())
