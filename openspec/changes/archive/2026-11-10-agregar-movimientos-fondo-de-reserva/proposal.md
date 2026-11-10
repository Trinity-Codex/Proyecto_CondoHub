# Proposal

## Why

CondoHub calcula el aporte mensual, pero no permite conocer el saldo ni sus usos. El [Issue #8](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/8), RF21, es **Should** del PMV 27-nov: C5 debe estar disponible el miércoles 18 de noviembre para #55. Closes #8.

## What Changes

- Libro de movimientos por condominio: saldo inicial, aportes al emitir, egresos y ajustes documentados; saldo igual a su suma en pesos enteros.
- Ingreso único por período, obtenido de la suma de `DetalleGastoComun.monto_fondo_reserva`, dentro de la emisión y su auditoría C1.
- Egresos registrados solo por el administrador, con descripción, fecha, proveedor opcional y referencia del acuerdo autorizante.
- Pantalla de saldo y movimientos desde gastos comunes para administrador y comité; conserje y residente reciben 403, y los objetos ajenos, 404.
- Contrato `apps.gastos.fondo.saldo_fondo(condominio, hasta_periodo=None)` y consulta mensual de movimientos para #55, con corte temporal explícito.
- Configuración inicial en `apps/gastos`, sin modificar `apps/condominios`. Auditoría de movimientos manuales y demo ficticia.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `gastos-comunes`: ADDED «Fondo de reserva» y MODIFIED «Emisión del período», conservando las reglas actuales de emisión.

## Impact

Implementación posterior en modelos, una migración de `gastos`, `fondo.py`, servicios, formularios, vistas, rutas, plantillas, pruebas y `apps/gastos/demo.py`; ampliar la huella demo en `apps/core/tests.py`. Reutiliza C1, C6, `MontoField`, `pesos` y permisos existentes, sin dependencias nuevas. `design.md` fija C5 y registra las decisiones pendientes sobre históricos y apertura.

Fuera de alcance: detalle en rendición y aviso de cobro (#55), conciliación bancaria, integración con pagos, automatización de multas e intereses y gestión digital de acuerdos. #46 no aplica: esta pantalla muestra movimientos del condominio, sin residentes ni cobros individuales. Esta fase entrega solo planificación; requiere revisión antes de implementar.
