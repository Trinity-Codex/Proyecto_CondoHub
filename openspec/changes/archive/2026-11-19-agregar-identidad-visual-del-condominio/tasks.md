# Tasks

## 1. Validador compartido

- [x] 1.1 `apps/core/imagenes.py`: `validar_imagen`, `preparar_imagen` y `RutaAleatoria`; verificar formatos reales y disfrazados, SVG, archivo dañado, límites de peso y píxeles, EXIF, orientación y reducción en `apps/core/tests_imagenes.py`.

## 2. Modelo, pantalla y entrega

- [x] 2.1 Campos `logo` y `portada` en `Condominio` (migración 0003) y `MEDIA_ROOT`/`MEDIA_URL` sin ruta pública; pruebas que escriben en una carpeta temporal.
- [x] 2.2 «Datos del condominio» para el administrador, con auditoría y borrado del archivo anterior; verificar 403 para comité, conserje y residente.
- [x] 2.3 Vista `condominios:imagen`; verificar 200 para miembros, 404 para otro condominio y 302 sin sesión, y que `/media/` no responde.

## 3. Encabezado, demo y verificación

- [x] 3.1 Encabezado con nombre y logo en `templates/base.html`, portada solo en el panel; verificar contraste AA y anchos 375×812 y 1440×900.
- [x] 3.2 Logo y portada ficticios en `apps/condominios/demo.py`.
- [x] 3.3 `python manage.py test apps` completo.
