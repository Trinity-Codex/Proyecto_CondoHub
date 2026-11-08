"""
Datos demo de privacidad (Issue #51, cargar_demo por app).

Una solicitud pendiente de residente@condohub.cl (para que el administrador la responda
en la demo) y otra ya cerrada de residente2@condohub.cl. Usa lo que dejaron las apps
anteriores en "datos" (ver apps/core/management/commands/cargar_demo.py).

Se crean directo, sin presentar() ni cerrar(): así no generan avisos y no cambian la
"huella" de la demo que comprueba CargarDemoTest (apps/core/tests.py).
"""
from django.utils import timezone

from .models import SolicitudTitular


def cargar(datos):
    u, condominio = datos["usuarios"], datos["vista_verde"]
    SolicitudTitular.objects.create(
        usuario=u["residente"],
        condominio=condominio,
        tipo=SolicitudTitular.Tipo.RECTIFICACION,
        detalle="Mi teléfono cambió: el correcto termina en 4521. ¿Pueden actualizarlo en la ficha de la unidad?",
    )
    SolicitudTitular.objects.create(
        usuario=u["residente2"],
        condominio=condominio,
        tipo=SolicitudTitular.Tipo.ACCESO,
        detalle="Quiero saber qué datos míos tienen registrados.",
        estado=SolicitudTitular.Estado.CERRADA,
        respuesta=(
            "Tenemos tu nombre, RUT, correo, teléfono, tu residencia en B-102 desde el mes pasado y tus cobros desde "
            "esa fecha. Puedes descargarlos completos desde Mi perfil, en «Descargar mis datos»."
        ),
        cerrada=timezone.now(),
        cerrada_por=u["administrador"],
    )
