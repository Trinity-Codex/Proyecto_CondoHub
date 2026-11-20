# Design

## Context

- `DetalleGastoComun` (contrato con Winderson, #3 y #4) guarda `monto` (parte de los egresos) y `monto_fondo_reserva`; su propiedad `total` es la suma. Pagos, saldo, total adeudado, cobranza, descarga de datos y el reporte (`reportes.anotar_pagado`, que lo calcula en SQL con `F()`) parten de ese total.
- La emisión (`servicios.emitir_periodo`) bloquea el condominio y luego el período (`select_for_update`), calcula con `calcular_emision` y crea los cobros con `bulk_create`. `prorrateo.repartir` ya reparte con el método del resto mayor.
- Los egresos se protegen con `PeriodoAbiertoMixin`, pero sin bloqueo de filas: un egreso que llega justo durante la emisión no se rechaza. Para los ítems (dinero dirigido a unidades) se pide probar la concurrencia.
- El filtro de residencia (#46) se aplica sobre los cobros (`cobros_visibles`); lo que cuelgue de un cobro queda filtrado con él.

## Goals / Non-Goals

**Goals:**
- Que la suma cuadre: total del período = Σ cobros = egresos + fondo + Σ ítems, y cada ítem prorrateado suma exactamente su total.
- Que el total del cobro y el reporte incluyan los ítems sin que Winderson cambie su código.
- Que un ítem no pueda cambiar después de que el período se emitió, ni siquiera por concurrencia.

**Non-Goals:**
- Mostrar las líneas en el detalle del cobro del residente y en el estado de cuenta (PR posterior, tras #115).
- Motivo de la multa, respaldo y topes legales (consulta C2).

## Decisions

### 1. Dos modelos: `ItemCobro` (lo que se planifica) y `LineaCobro` (lo que se cobró)
`ItemCobro` pertenece al período y se edita mientras está abierto: `nombre`, `modo` (`POR_UNIDAD` o `PRORRATEO`), `monto`, `alcance` (`TODAS` o `ALGUNAS`), `unidades` (M2M, solo con `ALGUNAS`), `creado_por`. Al emitir se crea una `LineaCobro` por cada par (cobro, ítem) con monto mayor que cero: `detalle`, `item`, `nombre` (copia) y `monto`.

`LineaCobro.item` usa `RESTRICT`: un ítem ya cobrado no se puede borrar suelto (dejaría `monto_items` sin sus líneas), pero sí junto con su período o condominio. El panel `/admin/` muestra los ítems y las líneas solo para consulta; todo cambio pasa por la app, que bloquea el período y audita.

Alternativa descartada: calcular las líneas al vuelo desde `ItemCobro`. Si después cambia una alícuota o se agrega una unidad, el detalle de un mes ya cobrado cambiaría. Guardar la línea congela lo cobrado, igual que `DetalleGastoComun` congela la parte de los egresos.

### 2. `monto_items` en `DetalleGastoComun` y `total` lo incluye
Campo nuevo `monto_items` (entero positivo, 0 por defecto) = Σ de las líneas del cobro. `total = monto + monto_fondo_reserva + monto_items` y `reportes.anotar_pagado` suma la misma columna. Así pagos, saldo, total adeudado, cobranza y morosidad incluyen los ítems sin tocar `apps/pagos`. Los cobros ya emitidos quedan con 0: no cambian. Es un cambio aditivo al contrato; se avisa a Winderson en el PR.

Alternativa descartada: que `total` sume las líneas con una consulta. Rompería el cálculo en SQL del reporte y haría una consulta por cobro.

### 3. Los dos modos de monto y el redondeo
- **Por unidad:** cada unidad alcanzada paga `monto`. No hay redondeo: Σ = `monto × unidades alcanzadas`.
- **Total a prorratear:** `repartir(monto, {unidad: alícuota})` solo entre las unidades alcanzadas. `repartir` normaliza por la suma de sus pesos, así que con «algunas unidades» la alícuota se usa como proporción entre ellas. Cada unidad recibe la parte entera y los pesos sobrantes van, de a uno, a las de mayor parte decimal (desempate por id): la suma es **exactamente** el total del ítem. Se usa siempre la alícuota, aunque el período reparta los egresos en partes iguales, porque la cuota extraordinaria se cobra por alícuota (Ley 21.442); se confirma con el cliente.
- Cada ítem se reparte por separado. Así cada línea cuadra con su ítem y la suma de todo cuadra con el total del período.
- Si las alcanzadas suman alícuota 0, la emisión se rechaza nombrando el ítem (no se pierde el cobro en silencio).

### 4. Sin fondo de reserva sobre los ítems
El fondo es un porcentaje de los gastos ordinarios (los egresos). Una multa o una cuota extraordinaria no aportan al fondo; el ingreso al fondo sigue siendo Σ `monto_fondo_reserva`.

### 5. Alcance «todas» se resuelve al emitir
Un ítem general alcanza a las unidades que existan al emitir, igual que los egresos. Con «algunas», el formulario ofrece solo unidades del condominio activo y exige al menos una.

### 6. Concurrencia: mismo orden de bloqueos que la emisión
Guardar o eliminar un ítem pasa por un servicio que, dentro de `transaction.atomic`, bloquea el condominio y luego el período (el mismo orden que `emitir_periodo`, sin riesgo de interbloqueo) y vuelve a revisar que el período siga abierto. Si la emisión ganó, el cambio se rechaza con el aviso de período emitido. La auditoría se registra en la misma transacción.

### 7. Límite por cobro
Al emitir, si el total de un cobro supera `MONTO_MAXIMO` ($999.999.999), se rechaza: evita desbordar la columna y montos absurdos por error de tipeo.

### 8. Vistas
`ItemCobroCreateView`, `ItemCobroUpdateView` y `ItemCobroDeleteView` con `RolRequeridoMixin` (solo administrador), `CondominioQuerysetMixin` (`periodo__condominio`) y `PeriodoAbiertoMixin`. La lista va en el detalle del período (administrador y comité), como los egresos. Las rutas nuevas de escritura son `periodos/<pk>/items/nuevo/`, `items/<pk>/editar/` e `items/<pk>/eliminar/`.

## Risks / Trade-offs

- [El detalle del residente aún no muestra las líneas en este PR] → El total ya las incluye; el PR siguiente agrega las líneas en `pagos/detalle.html` y el estado de cuenta tras unir #115.
- [Cambio del contrato `DetalleGastoComun`] → Aditivo, con 0 por defecto; ningún código existente se rompe. Se avisa a Winderson.
- [El modo prorrateado con partes iguales en el período puede sorprender] → Se documenta en la ayuda del formulario y se confirma con el cliente.
- [PR #112 aún sin unir] → Las rutas de escritura se anotan en el PR para agregarlas a `middleware_demo.py`.

## Migration Plan

Una migración (`0008`): crea `ItemCobro` y `LineaCobro` y agrega `monto_items` con 0 por defecto. Reversible; sin datos que convertir.

## Open Questions

- Consulta C2: si la multa necesita motivo o respaldo visible y si hay topes. Se agrega después como campo opcional sin cambiar este diseño.
