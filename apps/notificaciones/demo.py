"""
Datos demo de notificaciones (Issue #62).

No crea nada: las notificaciones de la demo salen solas del patrón Observer al publicar
comunicados, reportar incidentes y registrar pagos (ver observador.py).

Recordatorios de pago (Issue #57): tampoco se crean aquí, porque dependen del día en que
se carga la demo y cambiarían la cantidad de notificaciones que comprueba CargarDemoTest.
Para verlos en la demo, simula un día cercano al vencimiento del mes anterior (el día 10
de este mes, ver gastos/demo.py):

    python manage.py enviar_recordatorios --fecha AAAA-MM-08   # 2 días antes: aviso previo
    python manage.py enviar_recordatorios --fecha AAAA-MM-11   # 1 día después: aviso de vencido

Luego entra como residente@condohub.cl y revisa la campana.
"""


def cargar(datos):
    """Sin datos propios (ver el comentario del módulo)."""
