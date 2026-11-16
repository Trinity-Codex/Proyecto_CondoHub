# Tasks

Este cambio cubre el Issue #27 en tres PR: el núcleo (secciones 1 a 4, ya unido), la vista (sección 5, `Refs #27`) y los eventos de pagos e incidentes (sección 6, `Closes #27`). La anulación de pagos ya registra su evento desde #53.

## 1. Modelo e inmutabilidad

- [x] 1.1 Crear `RegistroAuditoria` en `apps/auditoria/models.py` con los campos `condominio_id` (número, sin FK, según la firma aprobada), `condominio_nombre`, `usuario_id`, `usuario_nombre`, `accion`, `objeto_tipo`, `objeto_id`, `antes` (JSON, nulo), `despues` (JSON, nulo) y `creado`. Verificación: `python manage.py makemigrations auditoria` genera `0001_initial` (el nombre que usan todas las apps).
- [x] 1.2 Agregar `QuerySet` propio con `update()` y `delete()` que lanzan `RegistroInmutable`, y `save()` y `delete()` del modelo con la misma excepción si la fila ya existe. Verificación: prueba que intenta modificar y borrar un registro y comprueba que la fila no cambió.
- [x] 1.3 Registrar el modelo en el admin de Django sin permisos de cambio ni de borrado. Verificación: prueba que el admin devuelve `False` para `has_change_permission` y `has_delete_permission`.
- [x] 1.4 Crear la migración `0001_initial` y verificar con `python manage.py makemigrations --check`.

## 2. Servicio `registrar()`

- [x] 2.1 Crear `apps/auditoria/servicios.py` con `registrar(usuario, condominio, accion, objeto, *, antes=None, despues=None)`. Guarda `condominio_id` y `condominio_nombre`, `usuario_id` y `usuario_nombre` (copiados en ese momento), `objeto_tipo = objeto._meta.model_name` y `objeto_id = objeto.pk`. Verificación: prueba con un usuario, un condominio y un objeto de prueba; comprueba todos los campos y la fecha.
- [x] 2.2 Guardar `antes` y `despues` como diccionarios con solo los campos que cambian, y dejar `None` cuando no se pasan. Verificación: prueba con valores anteriores y nuevos, y prueba sin ellos.
- [x] 2.3 Índices en `(condominio, creado)` y `(usuario_id)`. Verificación: `makemigrations --check` pasa y la migración incluye ambos índices.

## 3. Pruebas del núcleo

- [x] 3.1 Pruebas en `apps/auditoria/tests.py` para cada escenario de la spec: cambio con valores anteriores y nuevos, evento sin valores anteriores, intento de editar o borrar, y que el registro sobrevive si se borra el usuario. Verificación: `python manage.py test apps.auditoria` pasa.
- [x] 3.2 Verificar que la página provisional sigue respondiendo 403 a conserje y residente. Verificación: las pruebas existentes de `PaginaProvisionalTest` pasan sin cambios.
- [x] 3.3 Crear `apps/auditoria/demo.py` con registros de ejemplo para la demo del PMV. Verificación: `python manage.py cargar_demo` termina sin errores.

## 4. Verificación final del PR

- [x] 4.1 Ejecutar `python manage.py test apps` completo. Verificación: todas las pruebas pasan.
- [x] 4.2 Ejecutar `openspec validate agregar-registro-de-auditoria --strict` y `openspec validate --all --strict`. Verificación: ambos comandos pasan.
- [x] 4.3 Revisar que `apps/auditoria/servicios.py` y `models.py` tengan comentarios en español que expliquen el porqué de la inmutabilidad y de los campos sin clave foránea. Verificación: lectura del archivo por un compañero que no lo escribió.

## 5. Vista de auditoría (PR 2, `Refs #27`)

- [ ] 5.1 Reemplazar la página provisional de `AuditoriaInicioView` por una lista de `RegistroAuditoria` para el administrador y el comité. Filtra con `condominio_id=request.condominio.pk` porque el campo no es FK y `CondominioQuerysetMixin` no sirve. Verificación: prueba en la que el administrador y el comité ven los registros de su condominio y no los del condominio «Ajeno».
- [ ] 5.2 Filtros por fecha (desde y hasta, inclusive) y por usuario, en un formulario GET. Los filtros se aplican sobre el queryset ya limitado al condominio. Verificación: pruebas de cada filtro, y prueba de que filtrar por un usuario o una fecha de otro condominio no devuelve sus registros.
- [ ] 5.3 Vista de solo lectura: solo acepta GET. Sin enlaces de edición ni de borrado. Verificación: prueba de que un POST responde 405 y no crea ni cambia registros.
- [ ] 5.4 Residente y conserje reciben 403. Sin sesión, redirige al login. Verificación: se actualizan las pruebas de `PaginaProvisionalTest`, porque ahora el comité entra con 200.
- [ ] 5.5 Ejecutar `python manage.py test apps.auditoria` y `openspec validate agregar-registro-de-auditoria --strict`. Verificación: ambos pasan.

## 6. Eventos de pagos e incidentes (PR 3, `Closes #27`)

- [ ] 6.1 Registrar el evento al registrar un pago (`Pago.registrar`). Verificación: prueba del registro con `antes` vacío.
- [ ] 6.2 Registrar los cambios de estado de un incidente con el estado anterior y el nuevo. Verificación: prueba con `antes` y `despues`.

## Workflow follow-up

- Abrir el PR como borrador con `Refs #27`, avisar en el grupo que `registrar()` está listo para revisar, y esperar comentario de Walther o Maximiliano sobre la firma.
- Al terminar la vista (PR siguiente): `/opsx:archive` del cambio y `Closes #27`.
