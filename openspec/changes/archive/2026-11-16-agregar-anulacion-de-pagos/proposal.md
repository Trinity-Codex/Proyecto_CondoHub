## Por qué

Hoy un pago mal registrado solo se corrige desde `/admin/`. Para el cierre mensual, la corrección debe quedar a la vista y en la auditoría, con un motivo.

## Qué cambia

- El administrador anula un pago indicando un motivo obligatorio. El pago no se borra: queda marcado como anulado y el cobro recalcula su estado (vuelve a PENDIENTE si el pago anulado lo cubría).
- La anulación se registra en la auditoría (#27) y se avisa al residente.
- Los reportes y "Mi cuenta" ignoran los pagos anulados, mediante `Pago.objects.vigentes()` (contrato C4).

Issue: Closes #53. MoSCoW: Must, hito PMV 27-nov. Depende de #27 (contrato C1, `registrar()`).

## Fuera de alcance

- Editar un pago. Solo se anula y, si hace falta, se registra uno nuevo.
- Anular pagos desde el comité o el residente.
- Cambiar la forma de calcular la deuda total del cobro.
- Una línea en `apps/gastos/reportes.py` (`anotar_pagado`): el `Sum` filtra `pagos__anulado=False`. Se avisa a Walther al unir, porque es su archivo.
