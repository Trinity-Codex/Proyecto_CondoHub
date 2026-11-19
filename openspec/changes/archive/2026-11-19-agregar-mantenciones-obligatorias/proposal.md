Issue: #123 (RQ-08). Dos PR: este primero (modelo y calendario) con `Refs #123`; el segundo (alertas y certificados) con `Closes #123`. MoSCoW: Could, fase 2.
Fuera de alcance de este PR: ver «Qué queda para el PR 2».

## Why

El condominio hace mantenciones periódicas (recarga de extintores, revisión de red húmeda, ascensores, entre otras) y hoy
no hay dónde registrarlas ni ver cuáles están por vencer. El cliente lo pidió en la reunión del 16-nov (RQ-08).
Qué mantenciones lleva cada condominio y con qué frecuencia lo define el cliente (consulta C9): el sistema no afirma
que sean obligaciones legales.

## What Changes

- App nueva `apps/mantenciones` con los modelos `Mantencion` (nombre, frecuencia en meses, próxima fecha, proveedor
  opcional, anticipación en días con 15 por defecto) y `EjecucionMantencion` (fecha, observación, usuario).
- El estado (al día, por vencer, vencida) se calcula con la fecha de hoy; no se guarda.
- Calendario/lista ordenado por urgencia, con chips de estado y las insignias `.insignia-*` existentes.
- Crear, editar y registrar ejecución, solo para el administrador. Comité y conserje solo ven; el residente recibe 403.
- Al registrar una ejecución, la próxima fecha pasa a ser la fecha de ejecución más la frecuencia en meses de calendario.
- Cada alta, cambio y ejecución queda en auditoría (`registrar()`).
- Enlace «Mantenciones» en el menú para administrador, comité y conserje; datos demo ficticios en `demo.py`.

## Qué queda para el PR 2

- **Alertas** de vencimiento (notificación con el patrón Observer, comando de gestión idempotente y tarjeta en el panel de inicio).
- **Certificados** de mantención (JPG, PNG o PDF, máximo 5 MB): dependen de #116 (`apps/core/imagenes.py` y `MEDIA`), que aún no está unido.
- Las rutas de escritura en `apps/core/middleware_demo.py` (demo de Render, #111): ese archivo está en otro PR sin unir.

## Capabilities

### New Capabilities

- `mantenciones`: se agrega el requisito «Calendario de mantenciones». Los requisitos «Alertas de vencimiento» y
  «Certificados de mantención» se agregan en el PR 2.

### Modified Capabilities

Ninguna.

## Impact

- **Código:** `apps/mantenciones/` (modelos, migración `0001_initial`, vistas, plantillas, demo y pruebas); una línea en
  `config/settings.py`, una en `config/urls.py` y un enlace en `templates/base.html` (delegación de Walther en el Issue);
  pruebas del menú en `apps/core/tests.py`.
- **Migraciones:** una, solo en `apps/mantenciones`.
- **Dependencias externas:** ninguna (la suma de meses se hace a mano; `dateutil` no está en `requirements.txt`).
