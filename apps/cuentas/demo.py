"""
Datos demo de cuentas: un usuario por rol (Issue #62, cargar_demo por app).

cargar(datos) deja en datos["usuarios"] un diccionario {clave: Usuario}, ej.
datos["usuarios"]["administrador"]. Los usuarios no se borran con --reiniciar:
se reutilizan si ya existen (get_or_create).
"""
from apps.cuentas.models import Usuario

CLAVE_DEMO = "condohub2026"

# correo, nombre, apellido, RUT válido
USUARIOS = {
    "superadmin": ("superadmin@condohub.cl", "Super", "Administrador", "11.111.111-1"),
    "administrador": ("administrador@condohub.cl", "Ana", "Rojas", "12.345.678-5"),
    "comite": ("comite@condohub.cl", "Carlos", "Pérez", "13.579.246-2"),
    "conserje": ("conserje@condohub.cl", "Jorge", "Muñoz", "14.725.836-4"),
    "residente": ("residente@condohub.cl", "Valentina", "Soto", "15.975.346-8"),
    "residente2": ("residente2@condohub.cl", "Diego", "Castro", "16.482.759-3"),
    "residente3": ("residente3@condohub.cl", "Camila", "Fuentes", "17.258.369-5"),
}


def cargar(datos):
    usuarios = {}
    for clave, (correo, nombre, apellido, rut) in USUARIOS.items():
        usuario, creado = Usuario.objects.get_or_create(
            email=correo, defaults={"first_name": nombre, "last_name": apellido, "rut": rut}
        )
        if creado:
            usuario.set_password(CLAVE_DEMO)
            if clave == "superadmin":
                usuario.is_staff = usuario.is_superuser = True
            usuario.save()
        usuarios[clave] = usuario
    datos["usuarios"] = usuarios
