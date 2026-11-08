# Design

## Context

La app `apps/auditoria` existe desde el contrato C0 (#62) con una página provisional que solo verifica permisos
(`AuditoriaInicioView`, solo administrador). No tiene modelos. Los demás módulos todavía no llaman a ningún
registro de auditoría. Ver `proposal.md` para el motivo y la lista de eventos.

Restricciones que pesan en el diseño:
- Los registros deben sobrevivir a los cambios que registran, incluso si se borra el usuario o el objeto.
- Los datos personales que aparecen en los valores anteriores y nuevos también quedan guardados en el registro.
- Todas las apps llaman a la misma función, así que su firma es un contrato (C1).

## Goals / Non-Goals

**Goals:**
- Un único punto de entrada, `registrar()`, que cualquier app pueda llamar sin conocer el modelo.
- Inmutabilidad a nivel del modelo, del administrador y de los querysets, no solo de la interfaz.
- Un registro que no dependa de las claves foráneas de usuario ni de objeto para existir.

**Non-Goals:**
- La vista filtrable y los eventos de pagos e incidentes: van en el PR de vista (`Closes #27`).
- Protección a nivel de base de datos (triggers, permisos de solo inserción del usuario de MySQL): queda fuera de este Issue.
- Un historial completo del objeto (estado en cada fecha): solo se guarda el cambio.

## Decisions

**Modelo propio `RegistroAuditoria` en `apps/auditoria/models.py`.** Se guardan usuario, condominio, acción,
`objeto_tipo` y `objeto_id` como texto y entero, `antes` y `despues` como `JSONField` (nulos por defecto) y `creado`.
- Alternativa descartada: `django-simple-history`. Agrega tablas por modelo, exige fijar versiones y necesita
  middleware para saber quién hizo el cambio. Para una trazabilidad simple, un modelo propio es menos código.
- Alternativa descartada: relación genérica (`ContentType`). Obliga a una consulta extra para leer el tipo; un texto
  como `"pago"` o `"unidad"` basta para filtrar en la vista.

**El usuario y el condominio se guardan como texto y número, sin `ForeignKey` a usuario.** Si una cuenta se borra,
el registro debe seguir existiendo con el nombre que tenía en ese momento (`usuario_nombre`). Con una clave foránea
habría que elegir entre bloquear el borrado de la cuenta (`PROTECT`) o cambiar el registro (`SET_NULL`), y ambas
opciones rompen la inmutabilidad. El condominio también va sin clave foránea (`condominio_id`): con `PROTECT` se rompe `cargar_demo --reiniciar`, que borra el condominio demo.

**Inmutabilidad en tres niveles.**
- `RegistroAuditoria.save()` lanza `RegistroInmutable` si la fila ya existe, y `delete()` lanza la misma excepción.
- Un `QuerySet` propio redefine `update()` y `delete()` para que lancen la misma excepción.
- El admin de Django no ofrece cambiar ni borrar (`has_change_permission` y `has_delete_permission` devuelven `False`).

**`registrar()` se llama dentro de la misma transacción que el cambio.** Así, si el cambio falla, no queda un
registro de algo que no ocurrió. Cada app que llame a `registrar()` lo hace dentro de su `transaction.atomic()`.

**Valores anteriores y nuevos: solo los campos que cambian.** `antes` y `despues` reciben un diccionario con los campos
modificados, no el objeto completo. Esto limita la cantidad de datos personales que se copian en el registro.

**Índices** en `(condominio, creado)` y `(usuario_id)`, para la vista de filtros del PR siguiente.

## Risks / Trade-offs

- **Datos personales dentro del registro** → [Riesgo] que el registro sea en sí un dato personal sensible. → Mitigación:
  solo los campos que cambian, y el acceso queda restringido a administrador y comité (ver la spec).
- **Sin clave foránea al usuario** → [Riesgo] un `usuario_id` puede quedar apuntando a una cuenta inexistente.
  → Mitigación: es intencional, y `usuario_nombre` permite leer el registro sin la cuenta.
- **Inmutabilidad solo en el código de Django** → [Riesgo] alguien con acceso directo a MySQL puede editar una fila.
  → Mitigación: queda fuera de este Issue. Se menciona en la defensa como límite conocido.
- **Llamadas fuera de la transacción** → [Riesgo] una app olvida `transaction.atomic()`. → Mitigación: la regla va en
  la revisión del PR; cada prueba de evento verifica el registro después del cambio.

## Migration Plan

- Una migración nueva en `apps/auditoria` (`0001_inicial`). No hay datos previos que migrar.
- Rollback: revertir la migración borra la tabla. Antes del PMV no hay registros reales, así que no hay pérdida.
