# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-06) quiere estimar los gastos comunes del año siguiente a partir del año en curso, reajustados por IPC y por un crecimiento anual, en línea con la Ley 21.442. Hoy CondoHub no tiene proyección alguna: solo registra los egresos reales de cada período y los reparte al emitir.

Issue: Refs #121 (se cierra cuando el cliente confirme qué exige la ley para este cálculo). Prioridad MoSCoW: **Could**, hito PMV 27-nov (lo primero que se corta).

## What Changes

- **Proyección anual** (administrador y comité): toma como base los egresos de los períodos emitidos del año base, mes a mes; los meses sin período emitido se completan con el promedio de los meses reales y se marcan como estimados.
- **Parámetros por GET** (`?anio=…&ipc=…&crecimiento=…`): IPC anual y % de crecimiento ingresados por el usuario, con rangos validados; un valor inválido muestra el error del formulario, nunca un error 500.
- **Resultado por mes y por unidad**: egresos proyectados, fondo de reserva y total, repartidos con el criterio de prorrateo y el % del fondo vigentes (los del período más reciente). El total de cada mes es igual a la suma por unidad.
- **Cuadro de supuestos**: año base, año proyectado, IPC, crecimiento, criterio de prorrateo, % del fondo, meses reales y estimados.
- **Exportación CSV** con los mismos valores de la pantalla.
- Reproducible: con los mismos datos y parámetros, la proyección es idéntica.

Fuera del alcance:
- Fuente oficial automática del IPC (consulta C7): el valor lo ingresa el usuario.
- Los ítems de cobro (#117): son cargos puntuales y no entran en la base.
- Guardar la proyección o cambiar dinero: es una vista de solo lectura, sin auditoría.
- Validar el cálculo frente a la ley: lo confirma el cliente antes de cerrar el Issue.

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `gastos-comunes`: agrega el requisito «Proyección anual de gastos comunes».

## Impact

- `apps/gastos`: módulo nuevo `proyeccion.py` (solo lectura sobre `PeriodoGasto`, `Egreso` y `Unidad`), formulario de parámetros, dos vistas (pantalla y CSV), plantilla, enlace desde la lista de períodos y pruebas.
- Reutiliza `prorrateo.ESTRATEGIAS` y `apps/core/exportar.respuesta_csv`.
- Sin migraciones, dependencias nuevas ni cambios en la demo (el año demo ya tiene meses emitidos).
