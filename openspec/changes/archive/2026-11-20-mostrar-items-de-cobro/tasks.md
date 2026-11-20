# Tasks

## 1. Consultas

- [x] 1.1 Agregar `prefetch_related("lineas")` a la descarga de datos (la única que recorre las líneas de muchos cobros); verificar con una prueba de que dos cobros hacen las mismas consultas que uno.

## 2. Pantallas y PDF

- [x] 2.1 `pagos/detalle.html`: una línea por ítem (nombre y monto) entre el fondo de reserva y el total; verificar con una prueba de que el residente ve la cuota y su multa, y que gastos + fondo + líneas = total.
- [x] 2.2 `pagos/estado_cuenta.html`: columna «Ítems» oculta en el celular; verificar con una prueba y la UI a 1440×900 y 375×812.
- [x] 2.3 `pagos/pdf/aviso.html`: una fila por línea y «Intereses por mora»; verificar con una prueba sobre el HTML del aviso.
- [x] 2.4 Revisar el comprobante de pago (#56): no muestra el total del cobro, no requiere cambio.

## 3. Descarga de datos y demo

- [x] 3.1 `apps/privacidad/descarga.py`: exportar `gastos`, `fondo_reserva`, `items` y `lineas` de cada cobro; verificar con una prueba de que salen las líneas de su unidad y no las de otra.
- [x] 3.2 `apps/core/middleware_demo.py`: permitir POST a `gastos:item_nuevo`, `gastos:item_editar` y `gastos:item_eliminar` (#117); verificar con la prueba del middleware y que `cargar_demo` deja la cuota y la multa.

## 4. Pruebas por rol y cierre

- [x] 4.1 Pruebas: un residente no ve la multa de otra unidad en detalle, aviso ni descarga; el cobro de otra unidad y el de otro condominio responden 404.
- [x] 4.2 Correr `python manage.py test apps` completo y `openspec validate --all --strict` en verde.

## Workflow follow-up

- Archivar `agregar-items-de-cobro` (marcando su tarea 4.3) y este cambio en el mismo PR, con `Closes #117`.
- Anotar en el PR la consulta C2 pendiente (motivo o respaldo de la multa y topes).
