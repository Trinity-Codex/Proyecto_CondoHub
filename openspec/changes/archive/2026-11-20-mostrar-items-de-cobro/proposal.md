## Why

Desde el PR #125 (parte 1 de RQ-02) el total que ve el residente ya incluye los ítems de cobro (cuotas extraordinarias, multas), pero sin desglose: en su detalle aparece un total mayor que la suma de «Tu parte de los gastos» y el fondo de reserva, sin explicar la diferencia. El cliente pidió que cada ítem se vea como una línea separada, y la demo de Render debe mostrarlo antes de la entrega del 27-nov.

Issue: Closes #117 (RQ-02, parte 2). MoSCoW: Should, hito PMV 27-nov.

## What Changes

- Detalle del cobro del residente (`pagos/detalle.html`): una línea por ítem de cobro de su unidad (nombre y monto), entre el fondo de reserva y el total a pagar.
- Mi estado de cuenta (`estado_cuenta.html`): columna «Ítems» en escritorio; en el celular la columna se oculta como «Gastos» y «Fondo reserva».
- Aviso de cobro en PDF (#6): cada línea de ítem en vez de una sola fila «Ítems adicionales». La fila fija «Intereses y multas $0» pasa a «Intereses por mora $0», porque las multas ahora son ítems.
- Descarga de mis datos (#51): cada cobro exporta sus líneas de ítems y los montos de gastos, fondo e ítems.
- Demo de Render (#111): las tres rutas de escritura del mantenedor de ítems entran a la lista de POST permitidos.
- Se archiva también `agregar-items-de-cobro` (parte 1), que esperaba este PR.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities

- `pagos`: «Estado de cuenta del residente» agrega el desglose de los ítems de cobro en el detalle, el estado de cuenta, el aviso y la descarga de datos.

## Impact

- Código: plantillas de `apps/pagos` (detalle, estado de cuenta, aviso PDF), `apps/privacidad/descarga.py`, `apps/core/middleware_demo.py`.
- Sin modelos ni migraciones: usa `LineaCobro` y `DetalleGastoComun.monto_items` de la parte 1.
- El comprobante de pago (#56) no muestra el total del cobro, solo el saldo, así que no requiere desglose.

## Fuera de alcance

- Motivo o respaldo visible de la multa y topes legales o del reglamento (consulta C2 al cliente): se mostrará solo el nombre del ítem, que puede incluir el artículo del reglamento.
- Intereses por mora reales (hoy siempre $0).
- Cambiar el mantenedor de ítems o la emisión (parte 1, ya unida).
