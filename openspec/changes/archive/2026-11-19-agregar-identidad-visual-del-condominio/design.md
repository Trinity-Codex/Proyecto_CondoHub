# Design

## Context

Las imágenes del condominio son los primeros archivos subidos por usuarios en CondoHub. No había `MEDIA_ROOT` ni forma de servirlas, y RQ-07 y RQ-08 subirán fotos y certificados con las mismas reglas.

## Goals / Non-Goals

**Goals:** identificar el condominio activo en cualquier pantalla; que solo el administrador cambie logo y portada; que ninguna imagen se vea desde otro condominio ni sin sesión; dejar una pieza de validación reutilizable.

**Non-Goals:** almacenamiento en la nube (#29), recorte o edición de imágenes en el navegador, rediseño del panel.

## Decisions

- **No publicar `MEDIA_URL`.** En lugar de servir `media/` con `DEBUG` (lo que la expondría a cualquiera), la vista `condominios:imagen` entrega cada archivo después de revisar la sesión y que el condominio esté entre los del usuario. Otro condominio recibe 404, sin confirmar que exista. La URL lleva `?v=<id>`, así la respuesta puede guardarse en caché (`private`, un día) sin mostrar una imagen vieja.
- **Validar por contenido, no por extensión.** Pillow abre el archivo y se exige JPEG o PNG; SVG queda fuera por riesgo de XSS. El tope de 40 megapíxeles se revisa antes de decodificar.
- **Volver a codificar.** Se copian solo los píxeles a una imagen nueva: se pierden EXIF (GPS, cámara), perfiles y contenido pegado. Se respeta la orientación antes de descartarla. El logo se reduce a 512 px y la portada a 1920 px.
- **Nombre al azar** (`RutaAleatoria`, serializable para migraciones). Al reemplazar o quitar una imagen, el archivo anterior se borra recién cuando la transacción se confirma.
- **Encabezado solo con el nombre.** La dirección no aparece en todas las páginas: el aviso de privacidad no debe mostrar datos del condominio. La edición se abre desde el menú «Administración», no desde el encabezado.
- **Columnas con `default` y `db_default` vacíos**, para que las pruebas que migran hacia atrás otras apps puedan insertar condominios con el modelo antiguo.
- **Demo de Render**: la pantalla se puede ver (GET); guardar sigue bloqueado por el modo de solo lectura, porque abrir la subida de archivos en una demo pública dejaría a cualquiera cambiar el nombre y las imágenes. Las imágenes ficticias se generan con Pillow en `demo.py`, sin binarios en el repositorio.

## Risks / Trade-offs

- [Disco efímero en Render] → las imágenes se regeneran al preparar la demo; en producción se decide el almacenamiento en #29.
- [Archivos huérfanos si se borra un condominio] → hoy los condominios no se borran desde el sitio; `cargar_demo --reiniciar` puede dejar imágenes viejas en `media/` del PC local, que está ignorada por git.
