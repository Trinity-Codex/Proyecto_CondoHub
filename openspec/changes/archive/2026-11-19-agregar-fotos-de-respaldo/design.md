# Design

## Context

#116 ya trajo `MEDIA_ROOT` y `apps/core/imagenes.py` (formato real, sin EXIF, nombre al azar). Este cambio agrega el modelo, las vistas y la galería, y valida cada foto con `preparar_imagen`. Dónde viven los archivos en producción lo decide #29, así que la subida se enciende con `FOTOS_INCIDENTES_HABILITADAS` (apagada por defecto).

## Decisions

**`FotoIncidente` sin campo `condominio` propio.** Llega al condominio por el incidente (`incidente__condominio`), igual que `Reserva → espacio → condominio`. Las vistas usan `CondominioQuerysetMixin` con `campo_condominio = "incidente__condominio"`.

**Nombre de archivo generado.** `upload_to` guarda en `incidentes/<condominio_id>/<uuid>.<ext>`: nadie adivina la ruta ni cuela un nombre con datos personales.

**Validación en el formulario** (`CampoFotos`): extensión JPG/PNG, tamaño, y Pillow abre el contenido (un `.txt` renombrado a `.jpg` se rechaza). El formulario revisa primero sin abrir archivos (subida encendida y cantidad: existentes + nuevas) y después valida cada archivo con Pillow. Guarda el archivo con la extensión del formato que Pillow reconoció (JPEG→.jpg, PNG→.png), para que el Content-Type que se sirve coincida con los bytes. Después `preparar_imagen` (#116) vuelve a codificar la imagen sin EXIF. Las revisiones previas de extensión y tamaño solo dan mensajes propios de fotos y evitan abrir con Pillow un archivo ya inválido.
- Alternativa descartada: escribir aquí un validador propio completo. Duplicaría lo de #116.

**Archivos por una vista protegida, no por `MEDIA_URL`.** `FotoArchivoView` filtra con las mismas reglas del incidente (equipo del condominio ve todo; el residente solo las de sus incidentes) y responde 404 en cualquier otro caso. Entrega con `FileResponse`, `X-Content-Type-Options: nosniff` y `Cache-Control: private`.

**Reglas en el servicio, no en el formulario.** `FotoIncidente.subir()` se niega (`SubidaNoPermitida`) si la subida está apagada y cuenta el cupo dentro de `transaction.atomic` tras `select_for_update()` sobre el incidente, antes de escribir archivos; el formulario solo avisa antes. Si la transacción se revierte, `subir()` borra los archivos que alcanzó a escribir (el disco no participa en la transacción). La visibilidad (equipo ve todo, residente solo lo suyo) es un único helper, `solo_lo_visible`, usado por incidentes y fotos.

**Auditoría en el modelo.** `FotoIncidente.subir()` y `.eliminar()` llaman a `registrar()` dentro de su transacción, como `Incidente.cambiar_estado`. La baja audita antes de borrar y quita el archivo del disco solo al confirmarse la transacción (`on_commit`).

**Demo.** Las imágenes se generan con Pillow al cargar la demo (sin archivos en el repositorio) y solo en la demo del cliente y si la subida está encendida.

## Risks / Trade-offs

- El disco de Render Free es efímero: por eso la subida va apagada por defecto hasta que #29 decida el almacenamiento.
- Si se borra un incidente o un condominio, los archivos quedan huérfanos en disco (Django no los borra con la fila). Solo ocurre con `cargar_demo --reiniciar` o desde `/admin/`.
- Si el commit mismo falla después de que `subir()` terminó bien (caso raro), los archivos quedan huérfanos: no hay un gancho de rollback en Django.
- Con la subida apagada no se pueden adjuntar fotos: es intencional, mejor que perderlas en silencio al reiniciar.
