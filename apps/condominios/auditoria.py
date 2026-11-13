"""
Eventos de auditoría de cuentas y condominios (Refs #27, contrato C1).

Todo pasa por apps.auditoria.servicios.registrar(). Aquí están solo los datos que se
guardan de cada objeto: los mínimos para saber qué cambió (Ley 21.719: no se copian más
datos personales de los necesarios; registrar() además guarda solo los campos que cambian).

Se llama siempre dentro del mismo transaction.atomic() que el cambio: si el cambio falla,
no queda un registro de algo que no ocurrió.

    from apps.condominios.auditoria import datos_de, registrar_roles, roles_de
"""
from django.db import transaction

from apps.auditoria.servicios import Accion, registrar

from .models import Edificio, Membresia, Residente, Unidad


def datos_de(objeto):
    """Diccionario con lo que se audita de un edificio, una unidad, un residente o una persona."""
    if isinstance(objeto, Edificio):
        return {"nombre": objeto.nombre, "direccion": objeto.direccion}
    if isinstance(objeto, Unidad):
        return {
            "edificio": objeto.edificio.nombre,
            "numero": objeto.numero,
            "piso": objeto.piso,
            "tipo": objeto.tipo,
            # Texto con 6 decimales: 0.4 y 0.400000 son la misma alícuota y no cuentan como cambio.
            "alicuota": f"{objeto.alicuota:.6f}",
        }
    if isinstance(objeto, Residente):
        return {
            "persona": objeto.usuario.email,
            "unidad": str(objeto.unidad),
            "tipo": objeto.tipo,
            "activo": objeto.activo,
            "desde": objeto.desde,
            "hasta": objeto.hasta,
        }
    # Una cuenta (Usuario). recibir_correos es una preferencia, no un dato personal: no se audita.
    return {
        "correo": objeto.email,
        "nombre": objeto.first_name,
        "apellido": objeto.last_name,
        "rut": objeto.rut,
        "telefono": objeto.telefono,
    }


def roles_de(persona, condominio):
    """Roles activos de la persona en el condominio, ordenados (para comparar antes y después)."""
    return sorted(
        Membresia.objects.filter(usuario=persona, condominio=condominio, activo=True).values_list("rol", flat=True)
    )


def registrar_roles(actor, condominio, persona, antes):
    """Si los roles de la persona cambiaron respecto de `antes`, registra CAMBIAR_ROL."""
    despues = roles_de(persona, condominio)
    if despues != antes:
        registrar(actor, condominio, Accion.CAMBIAR_ROL, persona, antes={"roles": antes}, despues={"roles": despues})


def registrar_cambio(actor, condominio, objeto, antes):
    """CREAR (si antes es None) o MODIFICAR con los valores de antes y de ahora. Sin cambios, no registra nada."""
    despues = datos_de(objeto)
    if antes is None:
        registrar(actor, condominio, Accion.CREAR, objeto, despues=despues)
    elif antes != despues:
        registrar(actor, condominio, Accion.MODIFICAR, objeto, antes=antes, despues=despues)


class AuditarCambiosMixin:
    """
    Para CreateView y UpdateView de edificios y unidades: guarda y registra en una sola
    transacción. Va justo antes de CreateView/UpdateView en las clases base, para envolver
    el guardado real.
    """

    def form_valid(self, form):
        antes = None
        if getattr(self.object, "pk", None):  # UpdateView: el formulario ya cambió self.object en memoria
            antes = datos_de(type(self.object).objects.get(pk=self.object.pk))
        with transaction.atomic():
            respuesta = super().form_valid(form)
            registrar_cambio(self.request.user, self.request.condominio, self.object, antes)
        return respuesta
