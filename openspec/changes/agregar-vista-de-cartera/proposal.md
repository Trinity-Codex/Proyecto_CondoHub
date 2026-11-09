Issue: Closes #54. MoSCoW: **Must** (hito PMV 27-nov). Trazabilidad: RF18, RF20, NTI-08 y RNF08.
Fuera de alcance: editar datos desde la cartera, gráficos, PDF de la cartera, deuda por antigüedad y alertas.

## Why

La gerencia de Vita Gestión no puede ver la deuda de su cartera sin pedírsela a cada administrador (NTI-08):
cada reporte vive dentro de un condominio.

## What Changes

- Nuevo acceso **administrador general** (RF20): el superusuario le asigna condominios desde `/admin/`. Es solo
  de consulta y no da ningún rol dentro del condominio (no edita, no ve residentes ni pagos).
- Nueva página **Cartera** (`/cartera/`): una fila por condominio asignado para el mes elegido, con emitido,
  recaudado, % de recaudación, deuda anterior y unidades morosas, más una fila de totales y descarga en CSV.
  Las cifras salen del mismo cálculo del reporte de recaudación, así cuadran por construcción.
- Cada fila enlaza al **reporte de ese condominio** en modo consulta, dentro de la cartera, sin cambiar el
  condominio activo ni dar acceso a otras páginas.
- Sin nombres ni RUT de residentes, ni en la página ni en el CSV (RNF08).
- Asignar o quitar un condominio queda en el registro de auditoría (C1). Consultar la cartera no se audita.
- El menú muestra «Cartera» solo a quien tiene ese acceso y reemplaza la página provisional de C0, que hoy ven
  el administrador y el comité.
- Datos demo: un administrador general con los dos condominios demo.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `reportes`: se agrega «Vista de cartera» (ADDED).
- `condominios`: «Roles por condominio» (MODIFIED) describe el acceso de administrador general, que vive fuera
  de la membresía.

## Impact

- **Código (Walther):** `apps/cartera` (modelo `AsignacionCartera`, migración `cartera/0001`, admin, vistas,
  plantillas, `demo.py`, pruebas); `apps/gastos/views.py` y `reporte.html` (el reporte acepta un condominio
  dado, sin cambiar su cálculo); `apps/core` (descarga CSV compartida, variable del menú, página «sin
  condominio»); `templates/base.html`; `apps/gastos/demo.py` (un período emitido en Los Aromos).
- **Sin cambios en:** `apps/condominios`, `apps/auditoria`, `apps/cuentas`, `apps/pagos`. `reportes.py` no cambia:
  cuando C4 (#53) aplique `Pago.objects.vigentes()` en `anotar_pagado`, la cartera queda corregida sola.
- **Fuera de las carpetas de Walther (solo documentación):** la tabla de usuarios demo de `README.md` suma el
  correo del administrador general.
- **Dependencias externas:** ninguna.
