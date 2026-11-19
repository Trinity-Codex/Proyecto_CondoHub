## Por qué

El detalle de un cobro (`pagos/detalle.html`) mostraba al residente cada egreso con su descripción libre, categoría y monto: con los datos demo, «Sueldo conserje (jornada completa) $650.000». Eso expone remuneraciones individuales y, en datos reales, podría exponer nombres de trabajadores o terceros. Es el requerimiento RQ-09 del cliente y la única observación que corrige un riesgo (datos personales y permisos).

## Qué cambia

- Nueva función única `egresos_para_residente(periodo)` en `apps/pagos/consultas.py`: egresos agrupados por categoría con su subtotal. Las remuneraciones salen como una sola línea «Remuneraciones del personal». Sin descripción libre, proveedor ni fecha de boleta. La suma de los subtotales es exactamente `periodo.total_egresos()`.
- `CobroDetailView` y `pagos/detalle.html` la usan en lugar de `periodo.egresos.all()`. «Mi cuenta» no lista egresos y no cambia.
- Administrador y comité conservan el detalle completo en `gastos:periodo_detalle` (sin cambios en `apps/gastos`).
- El aviso de cobro (#6) y la rendición de cuentas (#55) deben reutilizar la misma función.

Issue: Closes #115 (RQ-09). MoSCoW: Must, hito PMV 27-nov.

## Fuera de alcance

- Cambiar modelos o migraciones.
- Ampliar el detalle para la rendición de cuentas (consulta C1 abierta con el cliente): se hará después sobre la misma función.
- Tocar `apps/gastos` o la plantilla para mostrar los ítems de cobro (RQ-02, #117).
