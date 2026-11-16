"""
Datos demo de proveedores (Issue #9): empresas que prestan servicios a Vista Verde.

Deja en datos["proveedores"] un diccionario {clave: Proveedor} para vincularlos a los
egresos (apps/gastos/demo.py). Incluye uno inactivo, para mostrar que se desactiva en
vez de borrar.

En la demo del cliente (hay "fecha_referencia_demo", Issue #98) Los Aromos también tiene dos
proveedores ficticios activos. No van en datos["proveedores"] (sigue siendo de Vista Verde) ni en egresos.
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
    if "fecha_referencia_demo" in datos:
        _proveedores_los_aromos(datos["los_aromos"])


def _proveedores_los_aromos(condominio):
    """Dos proveedores ficticios activos (RUT con dígito verificador correcto) para que la lista no salga vacía."""
    for rut, razon, rubro, contacto, telefono, correo in [
        ("76.543.210-3", "Jardines Ficticios Ltda.", "Jardinería", "Carla Soto", "+56 2 2111 0001", "contacto@jardinesficticios.example"),
        ("77.654.321-7", "Gasfitería Demo SpA", "Gasfitería", "Iván Rojas", "+56 9 5555 0002", "ventas@gasfiteriademo.example"),
    ]:
        Proveedor.objects.create(
            condominio=condominio, rut=rut, razon_social=razon, rubro=rubro,
            contacto=contacto, telefono=telefono, correo=correo,
        )
