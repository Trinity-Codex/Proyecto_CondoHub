## Context

La parte 1 (PR #125, cambio `agregar-items-de-cobro`) guarda al emitir una `LineaCobro` por ítem y unidad (con copia del nombre) y la suma en `DetalleGastoComun.monto_items`. Las pantallas de `apps/pagos` ya usan `cobro.total`, que incluye los ítems, pero no muestran las líneas. `cobros_del_residente` es la única fuente de los cobros que ve un residente (filtro de unidad y de residencia, #46).

## Goals / Non-Goals

**Goals:**
- Mostrar las líneas con el mismo filtro de acceso que ya usa cada vista, sin consultas extra por cobro.

**Non-Goals:**
- Mostrar quién creó el ítem, su modo (por unidad o prorrateado) o su alcance: son datos de la administración.

## Decisions

1. **Leer `LineaCobro`, no `ItemCobro`.** La línea es lo que se cobró a esa unidad y conserva el nombre aunque el ítem cambie. El residente nunca ve los ítems de otras unidades porque solo recibe las líneas de su propio cobro. Alternativa descartada: recalcular desde `ItemCobro`, que mostraría ítems de otras unidades y cambiaría si cambian las alícuotas.
2. **`prefetch_related("lineas")` solo donde se recorren las líneas de muchos cobros** (la descarga de datos): una consulta para todas, sin N+1. Basta `lineas` (no `lineas__item`) porque la línea ya trae nombre y monto. El detalle y el aviso muestran un solo cobro, así que `cobro.lineas.all()` es una consulta y no hay N+1. El estado de cuenta usa `monto_items` (ya en la fila), no las líneas. Alternativa descartada: precargar en `cobros_del_residente`, que agregaría una consulta inútil al panel, la lista y el aviso.
3. **Estado de cuenta: columna «Ítems»** oculta en el celular, igual que «Gastos» y «Fondo reserva» (RNF03): en 375 px se mantienen visibles total, estado y botón. El desglose por línea queda en el detalle.
4. **Aviso PDF: una fila por línea** con el nombre del ítem; si no hay ítems, no se agrega la fila. La fila fija «Intereses y multas $0» pasa a «Intereses por mora $0», para no contradecir una multa listada arriba.
5. **Descarga de datos:** cada cobro agrega `gastos`, `fondo_reserva`, `items` (suma) y `lineas` (lista de `{nombre, monto}`). Son claves nuevas: las existentes no cambian.

## Risks / Trade-offs

- [El nombre de un ítem es texto libre y podría nombrar a una persona] → solo lo ve la unidad a la que se cobró (la multa es de esa unidad). El motivo o respaldo visible queda pendiente de la consulta C2 al cliente.
- [Cobros emitidos antes de #117 no tienen líneas] → `monto_items` es 0 y no se muestra ninguna línea; el total no cambia.
