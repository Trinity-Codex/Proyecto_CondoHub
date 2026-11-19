# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-04) quiere que los comunicados normales también se lean: que el residente vea cuántos tiene pendientes, que el correo diga de qué trata y lleve al comunicado, que el administrador mida el porcentaje de lectura y que quien no lee reciba un recordatorio.

Issue: Closes #120. Prioridad MoSCoW: **Could**, agregado al hito PMV 27-nov. Depende de #118 (lectura por residente).

## What Changes

- **Contador de no leídos** junto a «Comunicados» en el menú, solo para el residente: comunicados vigentes que ve y no ha leído.
- **Correo al publicar** con el asunto «Nuevo comunicado: <título>» («Aviso importante: …» si es prioritario) y el enlace absoluto al comunicado (`SITIO_URL`). Tras iniciar sesión lleva al comunicado.
- **Porcentaje de lectura** por residente y por unidad en la lista, el detalle y la lectura por residente (administrador y comité).
- **Recordatorio automático** a quien no leyó un comunicado vigente después de N días (por defecto 3, configurable por condominio en «Recordatorios»), por la campana y por correo, una sola vez por persona y comunicado. Comando `enviar_recordatorios_comunicados`, idempotente, como los recordatorios de pago.

Fuera del alcance:
- Configurar un servicio SMTP real (#29); en desarrollo el correo sale por consola.
- Programar el comando en el servidor (#29). En la demo de Render se ejecuta a mano.

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `comunicacion`: modifica «Notificaciones automáticas» y «Confirmación de lectura»; agrega «Recordatorio de comunicados sin leer».

## Impact

- `apps/comunicados`: modelos `AjustesComunicados` y `RecordatorioComunicado` (migración 0004), `recordatorios.py`, comando, vista y plantilla de ajustes, porcentajes y pruebas.
- `apps/notificaciones`: `Evento.asunto` y suscripción del nuevo sujeto en `apps.py`.
- Delegado por Walther: el contador en `templates/base.html` y `apps/core/context_processors.py`.
- Sin dependencias nuevas.
