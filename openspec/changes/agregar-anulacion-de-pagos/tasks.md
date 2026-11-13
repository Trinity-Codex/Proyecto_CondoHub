## 1. Modelo y contrato C4

- [x] 1.1 Agregar a `Pago` los campos de anulación (anulado, motivo, fecha y quién anuló) en `apps/pagos/models.py`, con migración propia de `pagos`.
- [x] 1.2 Crear `Pago.objects.vigentes()` que excluye los anulados (contrato C4).
- [x] 1.3 Recalcular el saldo y el estado del cobro usando solo pagos vigentes.

## 2. Anulación

- [x] 2.1 Vista de anulación con `RolRequeridoMixin` (solo administrador) y `CondominioQuerysetMixin`; motivo obligatorio.
- [x] 2.2 Registrar la anulación con `apps.auditoria.servicios.registrar` (#27).
- [x] 2.3 Avisar al residente de la anulación con el Observer.

## 3. Sumas que ignoran anulados

- [x] 3.1 "Mi cuenta" y el panel de inicio usan `vigentes()`.
- [x] 3.2 `anotar_pagado` en `apps/gastos/reportes.py`: cambiar `Sum("pagos__monto")` por `Sum("pagos__monto", filter=Q(pagos__anulado=False))`. No usar `vigentes()` dentro del `Sum`: un queryset no es una expresión de agregado. Avisar a Walther al unir.

## 4. Pruebas y demo

- [x] 4.1 Pruebas en `apps/pagos/tests.py`: anulación que reabre el cobro, motivo obligatorio, 403 para comité y residente, 404 para otro condominio y suma sin anulados.
- [x] 4.2 Datos demo en `apps/pagos/demo.py`: un pago anulado visible en la demo.
- [x] 4.3 Correr `python manage.py test apps` completo y `openspec validate --all --strict`.

## 5. Cierre

- [ ] 5.1 Archivar este cambio en el mismo Pull Request, después de `avisar-pago-solo-a-quien-ve-el-cobro`, porque ambos modifican `Registro de pagos`.
