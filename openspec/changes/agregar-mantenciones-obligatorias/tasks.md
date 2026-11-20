# Tasks

Este cambio cubre el Issue #123 en dos PR: modelo y calendario (secciones 1 a 5, `Refs #123`) y alertas y certificados (sección 6, `Closes #123`).

## 1. Modelos y fechas

- [x] 1.1 Crear `Mantencion` y `EjecucionMantencion` en `apps/mantenciones/models.py` con la migración `0001_initial`. Verificación: `makemigrations --check` sin cambios y `migrate mantenciones zero` y de nuevo `migrate` sin errores.
- [x] 1.2 Estado calculado con `estado_en(hoy)`, sin campo guardado. Verificación: pruebas de `EstadoTest` (vencida, por vencer, al día y anticipación configurable).
- [x] 1.3 `sumar_meses` sin librerías nuevas. Verificación: `SumarMesesTest` (31-ene-2028 + 1 = 29-feb-2028; 29-feb-2028 + 12 = 28-feb-2029).
- [x] 1.4 `registrar_ejecucion` recalcula la próxima fecha y audita. Verificación: `EjecucionTest`.

## 2. Vistas y permisos

- [x] 2.1 Calendario ordenado por urgencia con chips y `.insignia-*`. Verificación: `ListaTest`.
- [x] 2.2 Crear, editar y registrar ejecución solo para el administrador; comité y conserje solo ven; el residente recibe 403. Verificación: `PermisosTest`.
- [x] 2.3 Aislamiento entre condominios (404 al editar o ejecutar una ajena; el proveedor de otro condominio se rechaza). Verificación: `AislamientoTest` y `CrearYEditarTest`.

## 3. Auditoría

- [x] 3.1 Alta, cambio y ejecución con `registrar()`. Verificación: `CrearYEditarTest` y `EjecucionTest`.

## 4. Registro de la app, menú y demo

- [x] 4.1 Una línea en `config/settings.py` y otra en `config/urls.py`, y el enlace «Mantenciones» en `templates/base.html` para administrador, comité y conserje. Verificación: `MenuAdministracionTest` en `apps/core/tests.py`.
- [x] 4.2 `apps/mantenciones/demo.py` con extintores (12 meses, por vencer), red húmeda (6, vencida) y ascensores (1, al día), sin afirmar que sean obligaciones legales. Verificación: `DemoTest`.
- [x] 4.3 `"mantenciones"` agregado a `APPS_DEMO` en `apps/core/management/commands/cargar_demo.py`, con los conteos de `CargarDemoTest` en `apps/core/tests.py` revisados (avisar a Walther).
- [x] 4.4 Rutas de escritura (`nueva/`, `<id>/editar/`, `<id>/ejecucion/`) en la lista de rutas permitidas de `apps/core/middleware_demo.py` (demo de Render, #111).

## 5. Verificación final del PR

- [x] 5.1 `python manage.py test apps` completo, `makemigrations --check --dry-run` y `openspec validate --all --strict`. Verificación: los tres pasan.
- [x] 5.2 Interfaz medida a 1440×900 y 375×812 con layout-inspector. Verificación: sin desbordes ni elementos cortados.

## 6. Alertas y certificados (PR 2, `Closes #123`)

- [ ] 6.1 Notificación (Observer) y comando de gestión idempotente cuando una mantención entra en su ventana de alerta, y tarjeta en el panel de inicio (avisar a Maximiliano).
- [ ] 6.2 Certificado o foto adjunta en la ejecución (JPG, PNG o PDF real, máximo 5 MB), cuando #116 esté unido.
