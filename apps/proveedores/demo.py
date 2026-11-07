"""
Datos demo de proveedores (Issue #9): empresas que prestan servicios a Vista Verde.

Deja en datos["proveedores"] un diccionario {clave: Proveedor} para vincularlos a los
egresos (apps/gastos/demo.py). Incluye uno inactivo, para mostrar que se desactiva en
vez de borrar.
"""
from apps.proveedores.models import Proveedor


def cargar(datos):
    condominio = datos["vista_verde"]
    fichas = {
        # clave: (RUT válido, razón social, rubro, contacto, teléfono, correo)
        "ascensores": ("76.123.456-0", "Ascensores Sur SpA", "Ascensores", "Marcela Tapia", "+56 2 2345 6789", "contacto@ascensoressur.cl"),
        "aseo": ("77.234.567-4", "Aseo Limpio Ltda.", "Aseo", "Roberto Díaz", "+56 9 8765 4321", "ventas@aseolimpio.cl"),
        "seguridad": ("78.345.678-8", "Seguridad Andes S.A.", "Seguridad", "Patricia Vera", "+56 2 2987 6543", "camaras@seguridadandes.cl"),
    }
    proveedores = {}
    for clave, (rut, razon, rubro, contacto, telefono, correo) in fichas.items():
        proveedores[clave] = Proveedor.objects.create(
            condominio=condominio, rut=rut, razon_social=razon, rubro=rubro,
            contacto=contacto, telefono=telefono, correo=correo,
        )
    # Inactivo: ya no trabaja con el condominio, pero se conserva su historial.
    Proveedor.objects.create(
        condominio=condominio, rut="79.456.789-1", razon_social="Jardines del Valle", rubro="Jardinería",
        contacto="Hugo Reyes", telefono="+56 9 5555 1234", activo=False,
    )
    datos["proveedores"] = proveedores
