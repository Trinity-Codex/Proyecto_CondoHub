"""
Datos demo de auditoría (Issue #27, cargar_demo por app).

Crea unos pocos registros para que la vista del PR siguiente tenga algo que mostrar.
Como los registros son inmutables, `cargar_demo --reiniciar` no los borra: el condominio
se recrea con otro id y los registros viejos quedan sin condominio vigente. Es aceptable
para datos de demostración (ver el comentario en `cargar_demo`).
"""
from apps.auditoria.servicios import Accion, registrar


def cargar(datos):
    admin = datos["usuarios"]["administrador"]
    vista_verde = datos["vista_verde"]

    # Primero la creación, para que la línea de tiempo de la vista quede en orden.
    # Es un evento sin valores anteriores, hecho por un comando (sin usuario).
    registrar(None, vista_verde, Accion.CREAR, vista_verde)
    # Un cambio con valores anteriores y nuevos: solo queda registrado el campo que cambió.
    registrar(
        admin, vista_verde, Accion.MODIFICAR, vista_verde,
        antes={"direccion": "Calle Antigua 100"},
        despues={"direccion": vista_verde.direccion},
    )
