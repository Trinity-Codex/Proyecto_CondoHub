"""
Datos demo de mantenciones (Issue #123): ejemplos ficticios de Vista Verde.

Las fechas salen de la fecha de referencia de la demo ("fecha_referencia_demo"; sin ella, hoy) para que siempre haya
una mantención vencida, una por vencer y una al día, sin importar cuándo se cargue. Son ejemplos: no se afirma que
sean obligaciones legales ni que esas sean sus frecuencias; eso lo define cada condominio.

`cargar_demo` la llama porque "mantenciones" está en APPS_DEMO (apps/core/management/commands/cargar_demo.py).
"""
from datetime import timedelta

from django.utils import timezone

from .models import Mantencion


def cargar(datos):
    condominio = datos["vista_verde"]
    proveedores = datos.get("proveedores", {})
    referencia = datos.get("fecha_referencia_demo") or timezone.localdate()
    fichas = [
        # (nombre, frecuencia en meses, días desde la referencia hasta la próxima fecha, proveedor)
        ("Recarga de extintores", 12, 10, None),  # dentro de los 15 días de anticipación: por vencer
        ("Revisión de red húmeda", 6, -12, None),  # fecha ya pasada: vencida
        ("Mantención de ascensores", 1, 25, proveedores.get("ascensores")),  # más allá de la ventana: al día
    ]
    for nombre, meses, dias, proveedor in fichas:
        Mantencion.objects.create(
            condominio=condominio, nombre=nombre, frecuencia_meses=meses,
            proxima_fecha=referencia + timedelta(days=dias), proveedor=proveedor,
        )
