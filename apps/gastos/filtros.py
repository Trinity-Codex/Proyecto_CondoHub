"""
Filtro `?situacion=` del reporte de recaudación (Issue #80, contrato definido en #79).

La clave de la URL se traduce a la `situacion` de cada `FilaReporte` ("Al día", "Pendiente", "Morosa").
Este mapa es el único lugar donde viven las claves: lo usan el reporte, su CSV y las tarjetas del inicio.
No cambia `generar_reporte` ni la regla de morosidad.
"""
SITUACIONES = {"al_dia": "Al día", "pendiente": "Pendiente", "morosa": "Morosa"}

# Color de la paleta (--estado-*) de cada situación.
COLOR_SITUACION = {"al_dia": "al-dia", "pendiente": "con-deuda", "morosa": "moroso"}

# Orden de urgencia: primero las que hay que cobrar.
_URGENCIA = {SITUACIONES[clave]: rango for rango, clave in enumerate(("morosa", "pendiente", "al_dia"))}


def ordenar_por_urgencia(filas):
    """Morosas, pendientes y al día; en cada grupo la mayor deuda primero. Estable: respeta el orden de la unidad."""
    return sorted(filas, key=lambda fila: (_URGENCIA[fila.situacion], -fila.deuda_total))
