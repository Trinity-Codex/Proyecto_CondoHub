# Tasks

## 1. Modelo y migración

- [x] 1.1 Crear `ItemCobro` y `LineaCobro` y agregar `monto_items` a `DetalleGastoComun` con `total` que lo incluya; verificar con `makemigrations gastos` (una sola migración `0008`) y `makemigrations --check`.
- [x] 1.2 Sumar `monto_items` en `reportes.anotar_pagado`; verificar con la prueba de que el total emitido del reporte cuadra con los cobros.

## 2. Cálculo y emisión

- [x] 2.1 Calcular las líneas de cada ítem en `calcular_emision` (por unidad y prorrateado por alícuota con `repartir`), con errores para ítems sin alícuota y cobros sobre el máximo; verificar con pruebas de cada modo y de suma exacta.
- [x] 2.2 Guardar `monto_items` y las `LineaCobro` en `emitir_periodo` dentro de la misma transacción; verificar con pruebas de emisión con ítems y de que el fondo no cambia.
- [x] 2.3 Servicio para guardar y eliminar ítems que bloquea condominio y período, revisa que siga abierto y audita; verificar con pruebas de auditoría y de período emitido (y de concurrencia en MySQL).

## 3. Mantenedor y pantallas

- [x] 3.1 Formulario `ItemCobroForm` (unidades solo del condominio activo, al menos una con «algunas») y vistas crear, editar y eliminar con `RolRequeridoMixin`, `CondominioQuerysetMixin` y `PeriodoAbiertoMixin`; verificar con pruebas de 403 (comité, conserje, residente), 404 (otro condominio) y validaciones.
- [x] 3.2 Plantillas: tarjeta de ítems en el detalle del período, columna de ítems en la vista previa de emisión y en el cobro por unidad, formulario y confirmación de eliminación; verificar la UI a 1440×900 y 375×812.

## 4. Demo, residencia y cierre

- [x] 4.1 Datos demo en `apps/gastos/demo.py`: una cuota extraordinaria general y una multa a una unidad; verificar con `cargar_demo` y su prueba.
- [x] 4.2 Prueba de que el residente solo obtiene las líneas de su unidad y de sus meses de residencia (#46) y de que el total adeudado las incluye.
- [x] 4.3 Correr `python manage.py test apps` completo y `openspec validate --all --strict` en verde.

## Workflow follow-up

- Anotar en el PR las rutas de escritura para `apps/core/middleware_demo.py` si #112 sigue sin unir.
- PR posterior (`Closes #117`), tras unir #115: líneas de ítems en `apps/pagos/templates/pagos/detalle.html` y en el estado de cuenta; archivar el cambio en ese PR.
