## 1. Modelo

- [x] 1.1 Crear `FotoIncidente` en `apps/incidentes/models.py` (incidente, imagen con nombre uuid, etapa, fecha, quién la subió) con una migración propia (`0002_fotoincidente`), probada hacia adelante y hacia atrás.
- [x] 1.2 `FotoIncidente.subir()` y `.eliminar()` registran la subida y la baja con `apps.auditoria.servicios.registrar`.

## 2. Subida y validación

- [x] 2.1 `CampoFotos` en `apps/incidentes/forms.py`: JPG/PNG reales, 5 MB por imagen, 10 por incidente, con mensajes claros y el `TODO(#116)` en el punto donde se enchufa el validador.
- [x] 2.2 El residente sube fotos «antes» al reportar (`IncidenteCreateView`, en la misma transacción que el incidente).
- [x] 2.3 `FotoSubirView`: administrador y conserje suben fotos «después». `FotoBorrarView`: solo administrador y conserje borran.

## 3. Visibilidad

- [x] 3.1 `FotoArchivoView` entrega el archivo con `FileResponse` aplicando la visibilidad del incidente (404 para otro residente u otro condominio).
- [x] 3.2 Galería antes/después con fecha y autor en `incidentes/detalle.html`.

## 4. Demo y pruebas

- [x] 4.1 Fotos ficticias en `apps/incidentes/demo.py` para el incidente resuelto de la demo del cliente (solo con `MEDIA_ROOT`); prueba en `tests_demo_datos.py`.
- [x] 4.2 Pruebas en `apps/incidentes/tests.py`: subida válida, rechazo de no-imagen, de más de 5 MB y de la foto 11, permisos por rol, aislamiento entre condominios y por URL directa, y auditoría.
- [x] 4.3 Correr `python manage.py test apps` completo y `openspec validate --all --strict`.

## 4b. Correcciones de la revisión de código

- [x] 4b.1 Sin `MEDIA_ROOT`: el formulario rechaza las fotos y `subir()` se niega con `SubidaNoPermitida`.
- [x] 4b.2 El cupo de 10 se cuenta en `subir()` dentro de la transacción con el incidente bloqueado (`select_for_update`); el formulario cuenta antes de abrir archivos con Pillow.
- [x] 4b.3 `subir()` borra los archivos escritos si la transacción falla (pruebas con fallo de auditoría).
- [x] 4b.4 Helper `solo_lo_visible` compartido por `IncidentesVisiblesMixin` y `FotoArchivoView`; `detalle.html` recibe `puede_gestionar` como booleano.
- [x] 4b.5 El archivo se guarda con la extensión del formato real (JPEG→.jpg, PNG→.png), así `FotoArchivoView` sirve el `Content-Type` correcto.

## 5. Pendiente (otros PR)

- [x] 5.1 Cuando se una #116: reemplazar `CampoFotos.validar_foto` por `apps.core.imagenes` (formato real y sin EXIF) y usar su configuración `MEDIA`.
- [x] 5.2 Agregar la ruta de subida (`incidentes:foto_subir`, `incidentes:nuevo`) a la lista de rutas permitidas de `apps/core/middleware_demo.py` cuando se una el PR de la demo de Render (#111). No se toca aquí porque está en otro PR sin unir.
- [ ] 5.3 Revisar la interfaz a 1440×900 y 375×812 con el navegador (no se pudo medir en esta entrega).
- [ ] 5.4 Archivar este cambio antes de unir (`/opsx:archive`).
