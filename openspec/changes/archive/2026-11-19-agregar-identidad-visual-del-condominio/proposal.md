# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-01) pidió que el administrador sepa siempre en qué condominio trabaja, sobre todo si gestiona más de uno, y una interfaz más amigable. Hoy el nombre aparece pequeño en la barra, no hay logo y no existe una pantalla para editar los datos del condominio.

Issue: Closes #116. Prioridad MoSCoW: **Must**, hito PMV 27-nov.

## What Changes

- **Encabezado del condominio** en todas las pantallas con condominio activo: nombre en grande y logo, también a 375 px. La portada se muestra solo en el panel de inicio, con un velo oscuro para mantener el contraste AA. El selector de condominio se conserva cuando hay más de uno.
- **Pantalla «Datos del condominio»** (solo administrador): nombre, dirección, comuna, logo y portada opcionales, con la opción de quitarlos.
- **Validador compartido de imágenes** (`apps/core/imagenes.py`): solo JPG y PNG reales, máximo 2 MB, tope de píxeles, imagen vuelta a codificar sin EXIF y nombre de archivo al azar. Lo reutilizan RQ-07 (#122) y RQ-08 (#123).
- **Entrega protegida de imágenes**: no son archivos públicos; una vista las entrega solo a miembros del condominio.
- Logo y portada ficticios en la demo (Vista Verde); Los Aromos queda sin imágenes.

Fuera del alcance:
- Almacenamiento persistente en producción (decisión de #29). El disco de Render Free es efímero; la demo regenera sus imágenes al cargar los datos.
- Rediseño del panel: solo el encabezado y su contraste.

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `condominios`: agrega «Identidad visual del condominio».

## Impact

- `apps/condominios`: campos `logo` y `portada` (migración 0003), formulario, vistas `datos` e `imagen`, plantilla, auditoría del condominio, demo y pruebas.
- `apps/core/imagenes.py` (nuevo) y sus pruebas.
- Delegado por Walther para este Issue: `config/settings.py` (`MEDIA_ROOT`, `MEDIA_URL`, carpeta temporal en las pruebas), `templates/base.html` (encabezado y menú), `static/css/condohub.css`, `.gitignore` (`media/`).
- Sin dependencias nuevas (Pillow ya estaba fijado).
