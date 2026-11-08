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

    No se usan `choices` en el campo a propósito: cada acción nueva obligaría a crear una
    migración en auditoria. En cambio, `registrar()` rechaza los textos que no estén aquí.
    """

    CREAR = "crear"
    MODIFICAR = "modificar"
    ANULAR = "anular"
    ELIMINAR = "eliminar"
    CAMBIAR_ROL = "cambiar_rol"

    @classmethod
    def validas(cls):
        return {valor for nombre, valor in vars(cls).items() if nombre.isupper()}


# Largo de `RegistroAuditoria.usuario_nombre`. Nombre y apellido juntos pueden pasar de 150
# caracteres; en MySQL estricto eso haría fallar el INSERT y, con él, el cambio de la app.
_LARGO_NOMBRE = RegistroAuditoria._meta.get_field("usuario_nombre").max_length

# Marca para "la clave no venía", distinta de "venía con valor None" (un dato que se borró).
_FALTA = object()


def _solo_cambios(antes, despues):
    """
    Deja solo los campos cuyo valor cambió. Guardar el objeto completo copiaría más datos
    personales de los necesarios en el registro (design.md, "solo los campos que cambian").
    Si solo viene uno de los dos diccionarios, se guarda tal cual. Si nada cambió, ambos
    quedan en None, igual que un evento sin valores.
    """
    if antes is None or despues is None:
        return antes, despues
    claves = set(antes) | set(despues)
    # Se compara con _FALTA para que {"rut": None} frente a {} cuente como cambio.
    cambiados = {k for k in claves if antes.get(k, _FALTA) != despues.get(k, _FALTA)}
    antes = {k: antes[k] for k in antes if k in cambiados}
    despues = {k: despues[k] for k in despues if k in cambiados}
    return antes or None, despues or None


def registrar(usuario, condominio, accion, objeto, antes=None, despues=None):
    """
    Guarda un registro de auditoría y lo devuelve.

    - `usuario`: quien hizo el cambio. Pasar `None` cuando lo hace un comando (cargar_demo,
      tareas programadas); el registro queda con `usuario_nombre="Sistema"`.
    - `condominio`: el objeto del condominio. Se guarda solo su id, sin clave foránea, para
      que el registro no dependa de que el condominio siga existiendo.
    - `accion`: una constante de `Accion`. Un texto que no esté ahí lanza ValueError.
    - `objeto`: el objeto afectado, ya guardado. Se guarda su tipo (`app.modelo`) y su id.
      Para registrar un borrado, llamar ANTES de `objeto.delete()`: después Django deja
      `pk=None` y no se sabría qué se borró.
    - `antes` y `despues`: diccionarios con los valores. Pasar `None` cuando no aplican.
    """
    if accion not in Accion.validas():
        raise ValueError(f"Acción desconocida: {accion!r}. Usa una constante de Accion.")
    if objeto.pk is None:
        raise ValueError("El objeto no tiene id: regístralo después de save() y antes de delete().")

    antes, despues = _solo_cambios(antes, despues)
    if usuario is None:
        usuario_id, usuario_nombre = None, "Sistema"
    else:
        usuario_id, usuario_nombre = usuario.pk, usuario.get_full_name() or usuario.get_username()

    return RegistroAuditoria.objects.create(
        condominio_id=condominio.pk,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre[:_LARGO_NOMBRE],
        accion=accion,
        # label_lower ("pagos.pago") no se confunde entre apps con modelos del mismo nombre;
        # concrete_model evita que un proxy guarde otro tipo para el mismo objeto.
        objeto_tipo=objeto._meta.concrete_model._meta.label_lower,
        objeto_id=str(objeto.pk),
        antes=antes,
        despues=despues,
    )
