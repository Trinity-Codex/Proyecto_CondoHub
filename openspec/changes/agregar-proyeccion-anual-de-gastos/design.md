# Design

## Context

RQ-06 (#121) pide estimar los gastos comunes del año siguiente. Los egresos reales están en `Egreso` (por `PeriodoGasto`), el reparto en `prorrateo.py` (Strategy con `repartir`, método del resto mayor) y el cálculo del fondo en `servicios.calcular_emision`. La fórmula exacta y la fuente del IPC están pendientes con el cliente (consulta C7), así que todo lo que sigue es un **supuesto provisorio** que se muestra en pantalla.

## Goals / Non-Goals

**Goals:** proyección por mes y por unidad, reproducible por URL, con cuadre exacto por redondeo y CSV idéntico a la pantalla.

**Non-Goals:** guardar proyecciones, IPC automático, ítems de cobro, cambiar la emisión.

## Decisions

1. **Fórmula (supuesto provisorio, C7).** Para cada mes `m` del año base, `proyectado_m = base_m × (1 + IPC/100) × (1 + crecimiento/100)`, calculado con `Decimal` y redondeado al peso (ROUND_HALF_UP) **una sola vez** al final. El IPC y el crecimiento se componen (no se suman) porque el crecimiento real se aplica sobre montos ya reajustados. Alternativa descartada: sumar porcentajes (`1 + (IPC + c)/100`), menos precisa con valores altos.

2. **Base.** `base_m` = suma de los egresos del período **emitido** del mes `m` del año base. Los períodos abiertos no cuentan: sus egresos aún pueden cambiar. Año base por defecto: el año en curso (`?anio=`, entre 2000 y 2100).

3. **Meses faltantes (a confirmar con el cliente).** Si un mes no tiene período emitido, `base_m` = promedio entero (ROUND_HALF_UP) de los meses reales del año base, y la fila se marca «estimado». Sin meses reales no hay proyección y se muestra un aviso.

4. **Ítems de cobro fuera de la base (supuesto).** Los ítems de #117 (cuotas extraordinarias, multas) son cargos puntuales que no se repiten el año siguiente; la base son solo los egresos. Si el cliente pide incluirlos, se agrega como otro parámetro.

5. **Criterio vigente.** El criterio de prorrateo y el % del fondo son los del período más reciente del condominio (abierto o emitido); sin períodos, alícuota y 5 % (los valores por defecto del modelo). Si el criterio es por alícuota y las alícuotas no suman 1, se muestra un aviso: el reparto sigue siendo proporcional, pero la emisión real lo rechazaría.

6. **Redondeo y cuadre.** Por mes: `fondo_m = round(proyectado_m × %fondo / 100)` (igual que la emisión). Luego `estrategia.calcular(proyectado_m, unidades)` y `estrategia.calcular(fondo_m, unidades)`; `repartir` garantiza que las partes suman exactamente cada total. El total del mes es `proyectado_m + fondo_m` = suma por unidad; los totales anuales son sumas de enteros, así que también cuadran.

7. **Parámetros.** Formulario GET con IPC entre −10 y 30 % y crecimiento entre −50 y 50 %, hasta 2 decimales; acepta coma o punto decimal. Vacíos valen 0. Inválidos: la pantalla muestra el error (200) y el CSV redirige a la pantalla con un mensaje.

8. **Una sola función de cálculo** (`proyeccion.proyectar`) alimenta la pantalla y el CSV, como `reportes.generar_reporte`, para que coincidan por construcción.

## Risks / Trade-offs

- [La ley o el cliente exigen otra fórmula] → el cálculo está aislado en `proyeccion.py` y documentado como supuesto; cambiarlo no toca vistas.
- [Con pocos meses reales, el promedio puede ser poco representativo] → la pantalla marca cuáles son estimados y cuántos meses reales hay.
- [Muchas unidades × 12 meses en una tabla ancha] → la pantalla muestra el detalle por unidad como total anual y mes a mes en una tabla con scroll horizontal propio; el CSV trae el detalle completo.
