"""
Prorrateo de los gastos comunes: patrón de diseño STRATEGY (Informe 2, sección 5.3).

Problema: el total de egresos del mes hay que repartirlo entre las unidades, y
el criterio puede cambiar. La Ley 21.442 dice que, por defecto, se reparte según
la ALÍCUOTA de cada unidad, pero el reglamento del condominio puede fijar otro
(por ejemplo, partes iguales). No queremos un if/else gigante en la vista.

Solución Strategy:
  - ESTRATEGIA (interfaz): EstrategiaProrrateo, con el método calcular().
  - ESTRATEGIAS CONCRETAS: PorAlicuota y PartesIguales. Cada una solo define
    cuánto "pesa" cada unidad.
  - CONTEXTO: la emisión del período (servicios.py) usa la estrategia que el
    período tenga elegida, sin saber cuál es.

Para agregar un criterio nuevo (ej. por consumo de agua) basta con crear otra
clase y registrarla en ESTRATEGIAS: no se toca la vista ni la emisión.
"""
from abc import ABC, abstractmethod
from decimal import ROUND_FLOOR, Decimal


def repartir(total, pesos):
    """
    Reparte un total en pesos chilenos (entero) según los pesos de cada unidad,
    SIN perder ni agregar pesos por el redondeo (método del resto mayor):

      1. Cada unidad recibe la parte entera de lo que le toca exactamente.
      2. Los pesos que sobran (por haber redondeado hacia abajo) se entregan,
         de a uno, a las unidades con la mayor parte decimal.

    Ejemplo: $100 entre 3 unidades iguales -> 33,33 cada una -> 33 + 33 + 33 = 99;
    sobra $1, que va a la primera unidad -> 34 + 33 + 33 = 100.

    pesos: diccionario {unidad: peso}. Devuelve {unidad: monto entero}.
    """
    suma_pesos = sum(pesos.values(), Decimal("0"))
    if total <= 0 or suma_pesos <= 0:
        return {unidad: 0 for unidad in pesos}

    exactos = {unidad: Decimal(total) * Decimal(peso) / suma_pesos for unidad, peso in pesos.items()}
    montos = {unidad: int(exacto.to_integral_value(rounding=ROUND_FLOOR)) for unidad, exacto in exactos.items()}

    sobrantes = total - sum(montos.values())
    # Orden: mayor parte decimal primero; si empatan, la unidad de menor id
    # (así el resultado es siempre el mismo, no depende del azar).
    por_decimal = sorted(exactos, key=lambda unidad: (-(exactos[unidad] - montos[unidad]), unidad.pk))
    for unidad in por_decimal[:sobrantes]:
        montos[unidad] += 1
    return montos


class EstrategiaProrrateo(ABC):
    """Interfaz de las estrategias de prorrateo."""

    nombre = ""  # texto que se muestra en la pantalla

    @abstractmethod
    def pesos(self, unidades):
        """Cuánto pesa cada unidad en el reparto: {unidad: peso}."""

    def calcular(self, total, unidades):
        """Reparte el total (entero, en pesos) entre las unidades: {unidad: monto}."""
        return repartir(total, self.pesos(unidades))


class PorAlicuota(EstrategiaProrrateo):
    """Ley 21.442 (criterio por defecto): cada unidad paga según su alícuota."""

    nombre = "Según la alícuota de cada unidad"

    def pesos(self, unidades):
        return {unidad: unidad.alicuota for unidad in unidades}


class PartesIguales(EstrategiaProrrateo):
    """Todas las unidades pagan lo mismo (si el reglamento así lo establece)."""

    nombre = "En partes iguales"

    def pesos(self, unidades):
        return {unidad: Decimal("1") for unidad in unidades}


# Estrategias disponibles. La clave es la que se guarda en el período
# (PeriodoGasto.criterio_prorrateo).
ESTRATEGIAS = {
    "ALICUOTA": PorAlicuota(),
    "PARTES_IGUALES": PartesIguales(),
}
