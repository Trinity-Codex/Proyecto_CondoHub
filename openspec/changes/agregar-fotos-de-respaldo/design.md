# Design

## Context

Hoy no hay almacenamiento de archivos en el proyecto: `MEDIA_ROOT` lo configura #116, que todavía no está unido. Este cambio avanza con el modelo, las vistas y la galería, y deja un único punto donde enchufar el validador de #116.

## Decisions

**`FotoIncidente` sin campo `condominio` propio.** Llega al condominio por el incidente (`incidente__condominio`), igual que `Reserva → espacio → condominio`. Las vistas usan `CondominioQuerysetMixin` con `campo_condominio = "incidente__condominio"`.

**Nombre de archivo generado.** `upload_to` guarda en `incidentes/<condominio_id>/<uuid>.<ext>`: nadie adivina la ruta ni cuela un nombre con datos personales.

**Validación en el formulario** (`CampoFotos`): extensión JPG/PNG, tamaño, y Pillow abre el contenido (un `.txt` renombrado a `.jpg` se rechaza). El límite de 10 por incidente se revisa en el formulario contando las fotos que ya tiene. Es provisional: #116 trae el validador definitivo, con EXIF; ahí se reemplaza `CampoFotos.validar_foto`.
- Alternativa descartada: escribir aquí un validador propio completo. Duplicaría lo de #116 y el Issue lo pide explícitamente.

**Archivos por una vista protegida, no por `MEDIA_URL`.** `FotoArchivoView` filtra con las mismas reglas del incidente (equipo del condominio ve todo; el residente solo las de sus incidentes) y responde 404 en cualquier otro caso. Entrega con `FileResponse`, `X-Content-Type-Options: nosniff` y `Cache-Control: private`.

**Auditoría en el modelo.** `FotoIncidente.subir()` y `.eliminar()` llaman a `registrar()` dentro de su transacción, como `Incidente.cambiar_estado`. La baja audita antes de borrar y quita el archivo del disco solo al confirmarse la transacción (`on_commit`).

**Demo.** Las imágenes se generan con Pillow al cargar la demo (sin archivos en el repositorio) y solo en la demo del cliente y si hay `MEDIA_ROOT`: sin él Django escribiría en la carpeta actual.

## Risks / Trade-offs

- Sin EXIF stripping hasta que se una #116: no debe llegar a producción sin él.
- El disco de Render Free es efímero: las fotos subidas allí no persisten; las ficticias se regeneran al cargar la demo.
- Si se borra un incidente o un condominio, los archivos quedan huérfanos en disco (Django no los borra con la fila). Solo ocurre con `cargar_demo --reiniciar` o desde `/admin/`.
- El límite de 10 fotos se revisa en el formulario, sin bloqueo: dos subidas simultáneas de la administración podrían pasarse por unas pocas.
