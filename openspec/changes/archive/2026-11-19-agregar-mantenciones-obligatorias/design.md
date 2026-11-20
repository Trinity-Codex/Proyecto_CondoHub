# Design

## Context

No hay hoy nada que lleve el calendario de mantenciones. Se sigue el patrón de `apps/proveedores`: vistas con
`RolRequeridoMixin` y `CondominioQuerysetMixin`, formularios Bootstrap y el servicio `registrar()` de auditoría.

## Decisions

**El estado se calcula, no se guarda.** Depende de la fecha de hoy y de la anticipación de cada mantención; un campo
guardado quedaría desactualizado cada medianoche. `Mantencion.estado_en(hoy)` lo calcula con
`timezone.localdate()` en las vistas. Vencida: la fecha ya pasó. Por vencer: faltan hasta `dias_anticipacion` días
(el mismo día cuenta como por vencer). Al día: el resto.

**La lista se ordena y cuenta en Python.** Un condominio tiene decenas de mantenciones, y calcular «fecha + N días» por
fila en SQL no es portable entre SQLite (pruebas) y MySQL (producción). Ordenar por próxima fecha ya deja las vencidas
primero. Si pasara de unos cientos de filas, se mueve el cálculo a la base y se pagina.

**Suma de meses propia (`sumar_meses`).** `timedelta` no suma meses y `dateutil` no está en `requirements.txt`. Si el mes de
llegada no tiene ese día, queda el último del mes (31-ene + 1 = 28 o 29-feb; 29-feb-2028 + 12 = 28-feb-2029).

**La próxima fecha parte de la fecha en que se hizo.** Así una mantención atrasada no acumula fechas pasadas. No se
acepta una fecha de ejecución futura. Registrar una ejecución antigua (después de otra más reciente) movería la próxima
fecha hacia atrás: riesgo aceptado, el administrador la puede corregir al editar.

**Auditoría dentro de la transacción.** Alta y cambio con `registrar()` en el mismo `transaction.atomic()` que el guardado;
la ejecución guarda la próxima fecha anterior y la nueva. Guardar sin cambiar nada no deja un registro vacío.

**El enlace del menú va fuera de «Administración»** porque el conserje no ve ese desplegable.

## Risks / Trade-offs

- Sin archivo adjunto en este PR (`# TODO(#116)` en `EjecucionMantencion`): se suma en el PR 2 con una migración propia.
- Sin alertas todavía: una mantención vencida solo se ve entrando al calendario.
