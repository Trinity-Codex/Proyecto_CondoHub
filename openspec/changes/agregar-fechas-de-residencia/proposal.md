# Proposal

Closes #46 · MoSCoW: **Must** · Hito PMV 27-nov · Contrato **C2** de `docs/equipo/PLAN_PMV_27NOV.md`.

## Why

Hoy un residente ve todos los cobros de su unidad, incluso los anteriores a su llegada, como la deuda del arrendatario anterior (RF19, detectado en la revisión de #38). El aviso de cobro (#6), el comprobante (#56) y los recordatorios (#57) necesitan la misma regla.

## What Changes

- Cada residencia guarda desde cuándo (obligatorio) y hasta cuándo (se completa al dar de baja).
- Un residente activo ve un período solo si su residencia se superpone con ese mes. Quien llega a mitad de mes ve el cobro completo (regla decidida por Maximiliano).
- El filtro se aplica a Mi cuenta, al detalle de un cobro (fuera de su período: 404) y a la tarjeta "Mi deuda" del inicio.
- Al asignar un residente, el administrador indica la fecha de inicio; no puede ser futura. Al reasignar a alguien dado de baja, la residencia parte de la nueva fecha.
- Las residencias existentes reciben una fecha que no les oculta ningún cobro que ya veían.
- La spec de condominios se pone al día con lo que ya existe desde #10: tipo familiar, baja, eliminación protegida y aviso de alícuotas.

**Fuera del alcance:**
- Cobranza y reporte de morosidad no cambian: la deuda sigue siendo de la unidad.
- Quien fue dado de baja no consulta sus cobros antiguos, igual que hoy.
- No se guarda un historial de varias residencias en la misma unidad.
- Los eventos de auditoría van en su propio PR (`Refs #27`).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `pagos`: «Estado de cuenta del residente» limita los cobros al período de residencia; «Cobranza por unidad» deja explícito que no se filtra.
- `condominios`: «Residentes de una unidad» incorpora fechas, tipo familiar y baja; se agregan la eliminación protegida y el aviso de alícuotas.

## Impact

- **Mis carpetas:** `apps/condominios` (modelo, migración con datos existentes, `residencias.py`, formulario, plantilla, admin, pruebas y `demo.py`).
- **Carpetas de otros (hay que avisar):**
  - `apps/pagos/consultas.py` (Winderson): aplicar `cobros_visibles`, excepción ya acordada.
  - `apps/core/pruebas.py` (Walther): **excepción nueva que requiere su visto bueno**. `crear_escenario()` debe fechar las residencias en el pasado, porque las pruebas usan cobros de meses anteriores.
- **Dependencia:** los datos demo requieren `apps/condominios/demo.py`, que crea #62 (lunes 9).
- **Contrato:** `cobros_visibles(cobros, usuario)`, para #6, #56 y #57.
