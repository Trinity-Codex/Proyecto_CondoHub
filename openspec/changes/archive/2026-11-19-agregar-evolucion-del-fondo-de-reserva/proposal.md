# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-05) quiere ver cuánto acumula el fondo de reserva y cómo evoluciona mes a mes, por edificio y por unidad. Hoy CondoHub solo muestra el saldo actual y el libro de movimientos del condominio, y únicamente al administrador y al comité.

Issue: Closes #119. Prioridad MoSCoW: **Should**, hito PMV 27-nov.

## What Changes

- **Evolución mensual** del fondo del condominio (administrador y comité): por cada mes, saldo de apertura, aportes, egresos, ajustes y saldo de cierre, que cuadra con el saldo de corte mensual ya existente. Gráfico de barras en SVG accesible, sin librería nueva, con una tabla equivalente de los mismos valores.
- Los meses sin período emitido aparecen marcados «sin período emitido», sin aporte inventado.
- **Aportes por edificio** mes a mes y **saldo por edificio** (aportes del edificio más su parte, según la alícuota, de los movimientos del condominio).
- **Aporte acumulado por unidad** y **por residente**, respetando las fechas de residencia (#46).
- **Desglose mensual de una unidad**: el administrador y el comité ven cualquiera de su condominio; un residente solo las suyas (otra unidad, 403).
- **Vista del residente**: saldo total del fondo y su propio aporte, nunca el de otras unidades (opción por defecto mientras responde la consulta C3).
- Datos demo con varios meses de historia.

Fuera del alcance:
- Fondos independientes por edificio (consulta C4): los egresos siguen registrándose a nivel de condominio.
- Exportar a CSV o PDF, y cualquier cambio de dinero: son vistas de solo lectura, sin eventos de auditoría nuevos.
- Los ítems de cobro (#117) no aportan al fondo y no aparecen en estas vistas.

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `gastos-comunes`: cambia «Fondo de reserva» para agregar la evolución mensual, el desglose por edificio, unidad y residente, y el acceso de lectura del residente a su propio aporte.

## Impact

- `apps/gastos`: módulo nuevo de consultas de evolución (solo lectura sobre `MovimientoFondo` y `DetalleGastoComun`), tres vistas, plantillas, enlaces desde el fondo y el menú, demo y pruebas.
- `apps/condominios` y `apps/pagos`: solo lectura (filtro de residencia `cobros_visibles`).
- `apps/core/tests*.py`: se actualiza la huella de la demo porque se agregan meses de historia.
- Sin migraciones ni dependencias nuevas.
