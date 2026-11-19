# Design

## Context

Ya existen el Observer de notificaciones (campana y correo), los recordatorios de pago (#57) con su constancia anti-duplicados y la lectura por residente (#118).

## Decisions

- **Asunto en el Evento.** `Evento.asunto` es opcional; si está vacío, el correo usa el título como antes. Así los demás sujetos no cambian. El asunto se deja en una sola línea, para que un salto de línea no haga fallar el envío.
- **Contador en el context processor**, solo con el rol residente: es una consulta `COUNT` sobre la misma regla de visibilidad de la lista (`visibles_para` + `vigentes`).
- **Porcentajes**: por residente (personas destinatarias activas) y por unidad (criterio de #58). Sin destinatarios, no se muestra porcentaje.
- **Plazo por condominio** en `AjustesComunicados` (fila 1 a 1, se crea al guardar). Sin fila vale 3 días.
- **Recordatorio idempotente**: `RecordatorioComunicado` (único por comunicado y persona) se crea antes de notificar, en la misma transacción. Ventana de 7 días después del plazo: cubre un día sin ejecución y evita recordar comunicados antiguos al activar la función.
- **Sin `__date` en la consulta**: el límite se calcula como fecha y hora local, porque MySQL sin tablas de zonas horarias no resuelve `__date` con `USE_TZ` (ver #128).

## Risks / Trade-offs

- [Correos de recordatorio a muchos residentes] → uno por persona y comunicado, y solo a quien acepta correos (`recibir_correos`).
- [La demo de Render no envía correos] → la campana, el contador y los porcentajes se ven con los datos ficticios.
