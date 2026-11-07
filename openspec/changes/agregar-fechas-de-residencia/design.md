# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver las specs de este cambio.

Estado actual que condiciona el diseño:

- `Residente` tiene `activo` y una restricción única (`usuario`, `unidad`): una persona que vuelve reutiliza la misma fila. No tiene fecha de creación.
- `cobros_del_residente()` (`apps/pagos/consultas.py`) es la fuente única de Mi cuenta, del detalle de un cobro y de "Mi deuda". Cobranza usa `unidad.cobros` y el reporte usa `periodo.detalles`, así que no pasan por ella.
- Un período se identifica por `anio` y `mes`; no tiene fechas propias.
- `crear_escenario()` y `cargar_demo` crean residentes sin fecha y luego cobros de meses pasados.

## Goals / Non-Goals

**Goals:**

- Una sola regla de visibilidad, reutilizable y que siga siendo un queryset encadenable.
- Migrar sin ocultar cobros que un residente ya veía.

**Non-Goals:**

- Historial de varias residencias por unidad y persona.
- Cambiar quién recibe notificaciones.

## Decisions

### D1. Contrato en `apps/condominios/residencias.py`

`cobros_visibles(cobros, usuario)` recibe un queryset de `DetalleGastoComun` y devuelve otro, filtrado con `Exists` sobre `Residente`.

- **Por qué `Exists`:** exige que usuario, unidad, `activo` y fechas se cumplan en la misma fila, no agrega filas duplicadas y evita una consulta por cobro.
- **Alternativa descartada:** filtrar en Python, que rompe el encadenamiento (`select_related`, `order_by`) y obliga a cada consumidor a cargar todo.

### D2. Superposición por año y mes

Un período se ve si `(año, mes)` de `desde` es menor o igual al del período y, si hay `hasta`, `(año, mes)` de `hasta` es mayor o igual. Se compara con `desde__year` y `desde__month` contra `OuterRef`.

- **Alternativa descartada:** agregar fechas al período, que exige una migración en `apps/gastos`, carpeta de Walther.

### D3. El filtro exige `activo=True`

Quien fue dado de baja no ve cobros de esa unidad, igual que hoy. Así la deuda de una unidad que ya dejó no se suma a "Mi deuda", y #57 no le recuerda pagarla. La condición sobre `hasta` expresa la regla completa y protege filas con `hasta` definido por otra vía.

- **Alternativa descartada:** permitir que el ex residente consulte su período. Requiere separar "consultar" de "deuda vigente" y se puede agregar después.

### D4. `save()` mantiene `hasta` coherente con `activo`

`Residente.save()` completa `hasta` con la fecha de hoy al desactivar y lo limpia al reactivar. Si la llamada usa `update_fields` con `activo`, también incluye `hasta`. Así funciona también desde `/admin/`, no solo desde `dar_de_baja()`.

Una `CheckConstraint` exige `hasta >= desde`. Como el formulario no admite `desde` futuro, una baja desde el sitio la cumple. Una baja desde `/admin/` de una fila con `desde` futuro falla con error: es un caso que solo ocurre editando a mano.

### D5. `desde` con valor por defecto

`desde = DateField(default=timezone.localdate)`. El formulario lo exige y admite fechas pasadas. Los `Residente.objects.create()` de otras apps siguen funcionando.

### D6. Migración conservadora

Una sola migración: agrega `desde` nulo, lo completa con `RunPython`, lo deja obligatorio y agrega `hasta` y la restricción. El valor es el menor entre:

- `Membresia.desde` del rol residente en ese condominio, y
- el primer día del cobro emitido más antiguo de esa unidad.

Si no hay ninguno, usa la fecha de la migración. El Issue sugería la fecha de creación, pero no existe ese dato. Usar solo la membresía podría ocultar cobros que hoy se ven.

Las filas ya inactivas quedan con `hasta` nulo, porque la fecha real se desconoce. Revertir la migración elimina los campos.

### D7. Corregir una fecha

No se agrega una pantalla de edición. El administrador da de baja y reasigna con la fecha correcta, o usa `/admin/` el superusuario.

## Risks / Trade-offs

- [Las pruebas con cobros de meses pasados dejan de verlos, porque `desde` sería hoy] → `crear_escenario()` fecha sus residencias en 2020. Toca `apps/core/pruebas.py` de Walther, excepción declarada en la propuesta.
- [`cargar_demo` deja a los residentes demo sin cobros en Mi cuenta] → fijar sus fechas en `apps/condominios/demo.py`. Si #62 se atrasa, pedir a Walther el cambio equivalente en `cargar_demo.py`, sin editarlo directamente.
- [Al reasignar se pierde la residencia anterior de esa unidad] → aceptado: no hay tabla de historial y lo adeudado sigue en la cuenta de la unidad.
- [La migración puede dejar ver una deuda ajena a un residente existente] → aceptado: es lo que ya ve hoy y se corrige reasignando.
- [Otro integrante usa `cobros_visibles` antes de que se una] → unir a más tardar el miércoles 11 y avisar la firma en el grupo.

## Migration Plan

1. Unir el PR y ejecutar `python manage.py migrate`.
2. Ejecutar `python manage.py cargar_demo --reiniciar` en cada PC para ver los datos demo nuevos.
3. Para revertir: `python manage.py migrate condominios 0001`.
