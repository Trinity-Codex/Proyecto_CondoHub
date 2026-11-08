# Tasks

Este cambio es el PR núcleo del Issue #27 (`Refs #27`). La vista y los eventos de pagos e incidentes van en el PR siguiente.

## 1. Modelo e inmutabilidad

- [ ] 1.1 Crear `RegistroAuditoria` en `apps/auditoria/models.py` con los campos `condominio` (FK, `PROTECT`), `usuario_id`, `usuario_nombre`, `accion`, `objeto_tipo`, `objeto_id`, `antes` (JSON, nulo), `despues` (JSON, nulo) y `creado`. Verificación: `python manage.py makemigrations auditoria` genera `0001_inicial`.
- [ ] 1.2 Agregar `QuerySet` propio con `update()` y `delete()` que lanzan `RegistroInmutable`, y `save()` y `delete()` del modelo con la misma excepción si la fila ya existe. Verificación: prueba que intenta modificar y borrar un registro y comprueba que la fila no cambió.
- [ ] 1.3 Registrar el modelo en el admin de Django sin permisos de cambio ni de borrado. Verificación: prueba que el admin devuelve `False` para `has_change_permission` y `has_delete_permission`.
- [ ] 1.4 Crear la migración `0001_inicial` y verificar con `python manage.py makemigrations --check`.

## 2. Servicio `registrar()`

- [ ] 2.1 Crear `apps/auditoria/servicios.py` con `registrar(usuario, condominio, accion, objeto, antes=None, despues=None)`. Guarda `usuario_id` y `usuario_nombre` (copiados en ese momento), y `objeto_tipo` y `objeto_id` tomados del objeto. Verificación: prueba con un usuario, un condominio y un objeto de prueba; comprueba todos los campos y la fecha.
- [ ] 2.2 Guardar `antes` y `despues` como diccionarios con solo los campos que cambian, y dejar `None` cuando no se pasan. Verificación: prueba con valores anteriores y nuevos, y prueba sin ellos.
- [ ] 2.3 Índices en `(condominio, creado)` y `(usuario_id)`. Verificación: `makemigrations --check` pasa y la migración incluye ambos índices.

## 3. Pruebas del núcleo

- [ ] 3.1 Pruebas en `apps/auditoria/tests.py` para cada escenario de la spec: cambio con valores anteriores y nuevos, evento sin valores anteriores, intento de editar o borrar, y que el registro sobrevive si se borra el usuario. Verificación: `python manage.py test apps.auditoria` pasa.
- [ ] 3.2 Verificar que la página provisional sigue respondiendo 403 a conserje y residente. Verificación: las pruebas existentes de `PaginaProvisionalTest` pasan sin cambios.

## 4. Verificación final del PR

- [ ] 4.1 Ejecutar `python manage.py test apps` completo. Verificación: todas las pruebas pasan (hoy son 243 según el README).
- [ ] 4.2 Ejecutar `openspec validate agregar-registro-de-auditoria --strict` y `openspec validate --all --strict`. Verificación: ambos comandos pasan.
- [ ] 4.3 Revisar que `apps/auditoria/servicios.py` y `models.py` tengan comentarios en español que expliquen el porqué de la inmutabilidad y de los campos sin clave foránea. Verificación: lectura del archivo por un compañero que no lo escribió.

## Workflow follow-up

- Abrir el PR como borrador con `Refs #27`, avisar en el grupo que `registrar()` está listo para revisar, y esperar comentario de Walther o Maximiliano sobre la firma.
- Al terminar la vista (PR siguiente): `/opsx:archive` del cambio y `Closes #27`.
