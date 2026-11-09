"""
Datos demo de cartera (Issues #62 y #54, cargar_demo por app).

Crea el administrador general ficticio «gerencia@condohub.cl» (misma clave que los demás usuarios demo) y le
asigna los dos condominios demo, con su evento de auditoría (hecho por el comando, así `usuario=None`). Con
`cargar_demo --reiniciar` los condominios se borran y las asignaciones se van con ellos (en cascada); el usuario
se reutiliza y las asignaciones se crean de nuevo. Deja la cuenta en datos["usuarios"]["gerencia"].
"""
from apps.auditoria.servicios import Accion, registrar
from apps.cuentas.demo import CLAVE_DEMO
from apps.cuentas.models import Usuario

from .models import AsignacionCartera

# correo, nombre, apellido, RUT ficticio válido
GERENCIA = ("gerencia@condohub.cl", "Gabriela", "Vidal", "18.273.645-7")


def cargar(datos):
    correo, nombre, apellido, rut = GERENCIA
    gerencia, creada = Usuario.objects.get_or_create(
        email=correo, defaults={"first_name": nombre, "last_name": apellido, "rut": rut}
    )
    if creada:
        gerencia.set_password(CLAVE_DEMO)
        gerencia.save()
    datos["usuarios"]["gerencia"] = gerencia

    for condominio in (datos["vista_verde"], datos["los_aromos"]):
        asignacion, nueva = AsignacionCartera.objects.get_or_create(usuario=gerencia, condominio=condominio)
        if nueva:
            registrar(
                None, condominio, Accion.CAMBIAR_ROL, asignacion,
                antes={"administrador_general": None}, despues={"administrador_general": gerencia.pk},
            )
