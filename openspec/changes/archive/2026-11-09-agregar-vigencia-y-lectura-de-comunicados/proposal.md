# Proposal

Closes #58 · MoSCoW: **Should** · Hito PMV 27-nov (se corta primero si hay atraso) · RF13 y NTI-05 (Informe 1).

## Why

Hoy los comunicados viejos se mezclan con los vigentes, y el administrador no sabe si los residentes leyeron un aviso importante (un corte de agua, una asamblea). RF13 pide consultar los comunicados vigentes.

## What Changes

- **Vigencia opcional («Visible hasta»):** al publicar o editar, el administrador puede poner una fecha. Desde el día siguiente, el comunicado sale de la lista principal y del panel de inicio. Un enlace «Ver vencidos» los muestra, con la insignia «Vencido», y el detalle se sigue abriendo por su enlace (por ejemplo, desde una notificación antigua).
- **Botón «Marcar como leído»** en el detalle, para el residente al que va dirigido el comunicado. Se puede marcar una sola vez.
- **Confirmaciones por unidad:** el administrador ve en la lista y en el detalle «X de Y unidades confirmaron». Una unidad cuenta como confirmada si cualquiera de sus residentes lo marcó, y Y son las unidades destinatarias que tienen residentes activos. En el detalle, también ve qué unidades faltan.
- Datos demo: una lectura de ejemplo y un comunicado vencido, sin agregar comunicados nuevos (la cantidad la comprueba `CargarDemoTest`).

**Fuera del alcance:**
- Recordatorios a quien no ha leído.
- Saber qué persona leyó: el conteo es por unidad, como pide el Issue.
- Lectura para el comité y el conserje: confirma el residente.
- Auditoría: la vigencia y la lectura no cambian dinero, roles ni datos personales.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `comunicacion`: MODIFIED «Visibilidad de comunicados» (la vigencia) y ADDED «Confirmación de lectura».

## Impact

- **Mis carpetas:** `apps/comunicados` (campo `vigente_hasta`, modelo `LecturaComunicado`, migración `0002`, vistas, formulario, plantillas, `demo.py` y pruebas) y el panel de inicio (`InicioView`), que muestra solo los vigentes.
- **Sin cambios** en `config/`, `templates/base.html` ni `requirements.txt`.
- **Piezas comunes:** `_formulario.html` (C6), `CampoFecha` e insignias `.insignia-*`.
