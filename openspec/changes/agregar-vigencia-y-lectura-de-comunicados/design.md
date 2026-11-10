# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver la spec `comunicacion` de este cambio.

Estado actual que condiciona el diseño:

- `ComunicadoQuerySet.visibles_para()` es la única regla de visibilidad: la usan la lista, el detalle y el panel de inicio.
- `Comunicado.destinatarios()` decide a quién se notifica: los residentes activos del condominio o del edificio, más el comité.
- `CargarDemoTest` (`apps/core/tests.py`) comprueba que la demo tenga 3 comunicados: no se agregan comunicados nuevos.
- Las piezas comunes de interfaz (C6, Issue #75 y siguientes): `_formulario.html`, `CampoFecha` e insignias `.insignia-*`.

## Goals / Non-Goals

**Goals:**

- Que los comunicados vencidos no molesten, sin perderlos.
- Un conteo de lectura honesto: por unidad y solo de las unidades a las que va dirigido.

**Non-Goals:**

- Recordatorios de lectura, lectura por persona y lectura del comité o del conserje.

## Decisions

### D1. Campo `vigente_hasta`

`DateField` opcional («Visible hasta») en `Comunicado`, migración `comunicados.0002`. Un comunicado está vencido si `vigente_hasta < hoy`: el día indicado todavía se ve.

- `ComunicadoQuerySet.vigentes(hoy)` y `.vencidos(hoy)` se encadenan con `visibles_para()`.
- El formulario rechaza una fecha anterior a hoy, salvo que sea la misma que ya tenía al editar (para poder corregir el texto de un comunicado vencido sin cambiar su fecha).

### D2. Lista principal y vencidos

- La lista y el panel de inicio muestran solo los vigentes.
- `?vigencia=vencidos` (con `FiltrosGetMixin`) muestra los vencidos. Se usa un enlace «Ver vencidos (N)» y no chips: los chips siempre traen «Todos» activo por defecto, y aquí lo normal es ver solo los vigentes.
- El detalle no filtra por vigencia: un enlace de una notificación antigua sigue funcionando. Muestra la insignia «Vencido».

### D3. `LecturaComunicado`: quién marcó

Modelo nuevo con `comunicado` (FK, CASCADE), `usuario` (FK, CASCADE) y `leido` (fecha y hora), con restricción única `(comunicado, usuario)`. Se guarda la persona y no la unidad: así cada residente ve su propio estado, y el conteo por unidad se calcula al mostrarlo (D4). Si la persona se muda, su lectura deja de contar para esa unidad.

### D4. Conteo por unidad

- **Unidades destinatarias (Y):** las del condominio, o las del edificio si el comunicado es por edificio, que tienen al menos un residente activo. Es el mismo criterio de `destinatarios()`.
- **Confirmadas (X):** las destinatarias con algún residente activo que tiene su `LecturaComunicado`.
- `Comunicado.confirmaciones()` devuelve `(confirmadas, destinatarias)` como conjuntos de unidades. En la lista se calcula solo para el administrador y para los comunicados de la página.

### D5. Marcar como leído

`MarcarLeidoView` (solo POST, `RolRequeridoMixin` con rol residente) busca el comunicado con `visibles_para()` (404 si no es para él) y crea la lectura con `get_or_create`: pulsar dos veces no duplica. Comité y conserje reciben 403. Vuelve al detalle con un mensaje.

### D6. Demo

Sin comunicados nuevos (ver Context): el «Corte de agua programado en Torre B» queda vencido desde ayer, y `residente2@condohub.cl` (Torre B) lo marca como leído. Así en la demo se ven «Ver vencidos (1)», la insignia y el conteo.

## Risks / Trade-offs

- **Cambios de residentes:** el conteo usa los residentes activos de hoy, no los del día de la publicación.
- **Consultas en la lista:** el conteo del administrador hace dos consultas por comunicado de la página (10 por página).
