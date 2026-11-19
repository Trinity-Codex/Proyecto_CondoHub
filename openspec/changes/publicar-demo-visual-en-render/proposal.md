# Proposal

## Why

Tras la presentación, el cliente necesita una URL donde recorrer CondoHub con datos ficticios. El entorno de revisión reutiliza el trabajo de #93 y el recorrido de #101.

Refs #111. Prioridad alta según el issue, fuera del hito PMV.

## What Changes

- Publicar una demo web HTTPS en Render Free con las pantallas y permisos existentes, identificada como solo lectura.
- Permitir navegación y autenticación por los flujos habituales. Bloquear en el servidor las escrituras de negocio, incluidos los GET con efectos de escritura.
- Reutilizar la SQLite aislada y los cargadores de demo. Reconstruir los datos ficticios al iniciar con almacenamiento vacío.
- Documentar el arranque, la operación y el recorrido desde la URL publicada.

## Capabilities

### New Capabilities

### Modified Capabilities

- `plataforma`: agrega un requisito para la publicación y el comportamiento del entorno de demo visual.

## Impact

La configuración de Render y la preparación de la demo viven en archivos dedicados. El entorno normal conserva MySQL y los permisos vigentes. Quedan fuera el despliegue productivo de #29, la persistencia, el correo real, los pagos externos y la subida de archivos.
