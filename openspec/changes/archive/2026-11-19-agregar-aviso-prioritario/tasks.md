# Tasks

## 1. Modelo y formulario

- [x] 1.1 Campo `prioritario` (migración 0003) y `avisos_pendientes()`; el formulario exige «Visible hasta» si es prioritario.

## 2. Bloqueo y confirmación

- [x] 2.1 `AvisoPrioritarioMiddleware` con rutas libres, solo para el rol residente y con falla abierta; registrar en `MIDDLEWARE`.
- [x] 2.2 Pantalla del aviso (de a uno, en orden) y confirmación por POST que vuelve a la página pedida.
- [x] 2.3 Verificar bloqueo con URL directa y POST, avisos vencidos o normales, roles, edificios, cerrar sesión, aislamiento y falla abierta.

## 3. Lectura, demo y verificación

- [x] 3.1 Vista de lectura por residente para administrador y comité (403 a residente y conserje, 404 desde otro condominio).
- [x] 3.2 Aviso ficticio para la Torre B en la demo del cliente y ruta de confirmación permitida en la demo de solo lectura.
- [x] 3.3 Revisar a 375×812 y 1440×900; `python manage.py test apps` completo.
