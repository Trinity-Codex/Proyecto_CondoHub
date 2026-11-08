"""
Punto único para registrar auditoría: `registrar()`.

Las apps lo llaman desde su propio `transaction.atomic()`, así el registro y el cambio
se guardan juntos o no se guardan. Si el cambio falla, no queda un registro de algo que
no ocurrió (ver design.md de #27).
"""
from apps.auditoria.models import RegistroAuditoria


class Accion:
    """
    Nombres de acción que se guardan en el registro. Usar estas constantes evita textos
    distintos para lo mismo ("crear" y "creado") que después no se pueden filtrar.
    Las apps que registren algo nuevo agregan aquí su constante.
    """

    CREAR = "crear"
    MODIFICAR = "modificar"
    ANULAR = "anular"
    ELIMINAR = "eliminar"
    CAMBIAR_ROL = "cambiar_rol"


def _solo_cambios(antes, despues):
    """
    Deja solo los campos cuyo valor cambió. Guardar el objeto completo copiaría más datos
    personales de los necesarios en el registro (design.md, "solo los campos que cambian").
    Si solo viene uno de los dos diccionarios, se guarda tal cual.
    """
    if antes is None or despues is None:
        return antes, despues
    claves = set(antes) | set(despues)
    cambiados = {k for k in claves if antes.get(k) != despues.get(k)}
    return (
        {k: antes[k] for k in antes if k in cambiados},
        {k: despues[k] for k in despues if k in cambiados},
    )


def registrar(usuario, condominio, accion, objeto, antes=None, despues=None):
    """
    Guarda un registro de auditoría y lo devuelve.

    - `usuario`: quien hizo el cambio. Pasar `None` cuando lo hace un comando (cargar_demo,
      tareas programadas); el registro queda con `usuario_nombre="Sistema"`.
    - `condominio`: el objeto del condominio. Se guarda solo su id, sin clave foránea, para
      que el registro no dependa de que el condominio siga existiendo.
    - `objeto`: el objeto afectado. Se guarda su tipo (nombre del modelo) y su id.
    - `antes` y `despues`: diccionarios con los valores. Pasar `None` cuando no aplican.
    """
    antes, despues = _solo_cambios(antes, despues)
    if usuario is None:
        usuario_id, usuario_nombre = None, "Sistema"
    else:
        usuario_id, usuario_nombre = usuario.pk, usuario.get_full_name() or usuario.get_username()

    return RegistroAuditoria.objects.create(
        condominio_id=condominio.pk,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=accion,
        objeto_tipo=type(objeto)._meta.model_name,
        objeto_id=str(objeto.pk),
        antes=antes,
        despues=despues,
    )
