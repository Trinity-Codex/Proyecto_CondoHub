## Por qué

Cuando la administración resuelve un incidente no queda evidencia de cómo estaba ni de cómo quedó. El cliente pidió (RQ-07, reunión del 16-nov) fotos de respaldo «antes» y «después» para tener ayuda memoria y justificar el trabajo ante la comunidad.

## Qué cambia

- Nuevo modelo `FotoIncidente` (imagen, etapa antes/después, fecha, quién la subió) con una migración propia de `incidentes`.
- El residente que reporta sube fotos «antes» al crear su incidente; el administrador y el conserje suben fotos «después» al gestionarlo o resolverlo. Solo ellos dos las borran.
- Límites: JPG o PNG reales, hasta 5 MB cada una y 10 por incidente, con mensajes claros.
- Galería en el detalle del incidente, separada en antes y después, con fecha y autor de cada foto. Todo incidente resuelto la muestra desde el historial.
- Los archivos no se sirven por `MEDIA_URL`: una vista protegida aplica la visibilidad del incidente.
- Subida y baja quedan en la auditoría (#27).
- Datos demo: el incidente resuelto de la demo del cliente trae fotos ficticias (color sólido con un rótulo, sin personas).

Issue: Closes #122 (absorbe #15). MoSCoW: Could, hito PMV 27-nov. Depende de #116 (`apps/core/imagenes.py` y la configuración `MEDIA`), que aún no está unido.

## Fuera de alcance

- Quitar los datos EXIF (ubicación) de las imágenes y validar con `apps/core/imagenes.py`: lo hace #116. En el punto exacto del código hay un `TODO(#116)` para enchufarlo; mientras no se una, las fotos se guardan tal como llegan.
- Configurar `MEDIA_ROOT` y `MEDIA_URL` (`config/settings.py`): también es de #116.
- Permitir la ruta de subida en el modo de solo lectura de la demo de Render (`apps/core/middleware_demo.py`): ese archivo está en otro PR sin unir; queda pendiente en `tasks.md`.
- Tareas internas distintas de los incidentes (consulta C8 del cliente): otro Issue.
- Subir fotos «antes» después de creado el incidente, o «después» el residente.
