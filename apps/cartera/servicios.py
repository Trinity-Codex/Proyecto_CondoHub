"""Auditoría del acceso de administrador general (Issue #54): un único lugar para el formato del evento."""
from apps.auditoria.servicios import Accion, registrar


def registrar_cambio_de_acceso(quien, asignacion, *, asignada):
    """
    Registra en el condominio de la asignación un `Accion.CAMBIAR_ROL`: el alta (`asignada=True`) o la baja.
    Guarda el id de la persona, nunca su nombre ni su RUT (RNF08). Para la baja, llamar ANTES de borrar la
    asignación: `registrar()` necesita su id. `quien` es None cuando lo hace un comando (cargar_demo).
    """
    antes, despues = (None, asignacion.usuario_id) if asignada else (asignacion.usuario_id, None)
    registrar(
        quien, asignacion.condominio, Accion.CAMBIAR_ROL, asignacion,
        antes={"administrador_general": antes}, despues={"administrador_general": despues},
    )
