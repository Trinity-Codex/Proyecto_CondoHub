# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-02) necesita agregar conceptos propios al cobro mensual, como una cuota extraordinaria o una multa. Hoy no se puede: cada cobro guarda solo la parte de los egresos y el fondo de reserva, y todo egreso se reparte entre todas las unidades.

Issue: Refs #117 (el último PR del Issue lleva `Closes #117`; absorbe #61). Prioridad MoSCoW: **Should**, hito PMV 27-nov.

## What Changes

- Nuevo **ítem de cobro** por período: nombre, monto entero en pesos, modo de monto y alcance.
  - Modo «monto por unidad»: cada unidad alcanzada paga ese monto (multas).
  - Modo «total a prorratear»: el total se reparte por alícuota entre las unidades alcanzadas, sin perder ni agregar pesos (cuotas extraordinarias).
  - Alcance: todas las unidades del condominio o solo las elegidas.
- Mantenedor de ítems (listar, crear, editar, eliminar) solo para el administrador y solo con el período abierto. Cada alta, cambio y baja queda en la auditoría.
- La **emisión** suma los ítems al cobro de cada unidad alcanzada y guarda una línea por ítem. El total del cobro, el saldo, el total adeudado y los reportes de recaudación y morosidad incluyen los ítems. Los ítems no generan aporte al fondo de reserva.
- La vista previa de emisión y el detalle del período muestran la columna de ítems.
- Datos demo: una cuota extraordinaria general y una multa a una unidad.

Fuera del alcance:
- Las líneas de ítems en el detalle del cobro del residente (`apps/pagos/templates/pagos/detalle.html`) y en el estado de cuenta van en un PR posterior, después de que se una #115 (RQ-09), que toca el mismo archivo. Este PR ya deja los datos listos y el total correcto.
- Motivo o respaldo visible de la multa y topes legales o del reglamento: pendientes de la consulta C2 al cliente. Se implementa lo básico.
- Cargos a una unidad después de emitir (un período emitido no admite cambios).
- El aviso de cobro en PDF (#6), que coordina Winderson.

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `gastos-comunes`: se agrega el requisito «Ítems de cobro» y cambia «Emisión del período» para sumar los ítems al cobro de cada unidad alcanzada.

## Impact

- `apps/gastos`: modelos `ItemCobro` y `LineaCobro`, campo `monto_items` en `DetalleGastoComun` (aditivo, con 0 por defecto; contrato con Winderson), una migración, servicios de emisión, vistas, formulario, plantillas, demo y pruebas.
- `apps/gastos/reportes.py`: el total del cobro incluye los ítems.
- `apps/core/middleware_demo.py` (PR #112, aún sin unir): las rutas nuevas de escritura se anotan en el PR para agregarlas.
