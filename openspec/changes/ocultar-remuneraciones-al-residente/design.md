## Decisión

Una sola función de consulta, `egresos_para_residente(periodo)`, en `apps/pagos/consultas.py` (junto a `cobros_del_residente`). Agrupa con un `GROUP BY categoria` y suma `monto`, así la suma de subtotales coincide con `total_egresos()` por construcción. Devuelve una lista de dicts `{"categoria", "subtotal"}` ordenada de mayor a menor subtotal.

## Por qué así

- Filtrar en la plantilla dejaría la regla repetida en cada pantalla o PDF; con una función, #6 y #55 la reutilizan.
- Agrupar en la base de datos evita que la descripción libre llegue siquiera al contexto de la plantilla.
- Las remuneraciones usan una etiqueta propia («Remuneraciones del personal») en vez del nombre de la categoría del modelo, para no tocar `apps/gastos`.

## Riesgo conocido

Un período con un solo egreso de remuneraciones revela ese monto en la línea agrupada. Es el nivel mínimo pedido en el Issue; si hace falta más protección, se ajusta en esta misma función.
