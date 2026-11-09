# Design

## Context

- `incidentes:lista` ya filtra por `?estado=` (botones `btn-group`, sin cantidades) y pasa `filtros_url` a `_paginacion.html`.
  Orden actual: `-fecha_reporte`.
- `UnidadesView` es un `ListView` de `Edificio` (sin paginar) con unidades y residentes en `prefetch_related`; no filtra.
- Los egresos salen de `PeriodoDetailView` (`self.object.egresos`, orden `fecha, pk`), sin filtro.
- El reporte (`ReporteMixin.preparar_reporte`, compartido por la página y el CSV) lee `periodo`, `edificio` y `solo_deuda`
  con `FiltroReporteForm`; `FilaReporte.situacion` devuelve «Al día», «Pendiente» o «Morosa». `InicioView` ya cuenta esas filas con
  `Counter` y deja un `TODO(#80)` en `_tarjetas_de_unidades`.
- Estados en insignias: `incidentes/_estado.html` y `gastos/_estado.html`/`_situacion.html` usan `.badge text-bg-*` de Bootstrap.
- `condohub.css` ya define `--estado-*`, `--estado-*-fondo` y `--estado-*-texto` (#79). No existen para «resuelto».

## Goals / Non-Goals

**Goals:** chips con cantidad, filtros por GET validados, orden por urgencia, insignias con la paleta propia, enlaces del panel
que abren el listado filtrado, `/proveedores/` sin desborde y base lista para #82.
**Non-Goals:** búsqueda `q`, `django-filter`, filtros de reservas, proveedores o pagos, cambios en `generar_reporte` o en la morosidad, migraciones.

## Decisions

**1. Qué listados y qué parámetros (reutiliza lo existente).**

| Listado | Parámetro | Valores | Origen |
|---|---|---|---|
| Incidentes | `estado` | `RECIBIDO`, `EN_PROCESO`, `RESUELTO` | ya existe; las tarjetas de #79 lo usan |
| Reporte de recaudación (y CSV) | `situacion` | `al_dia`, `pendiente`, `morosa` | contrato de #79 |
| Egresos del período | `categoria` | valores de `Egreso.Categoria` | nuevo |
| Unidades | `ocupacion` | `con_residentes`, `sin_residentes` | nuevo |

Las unidades no tienen estado propio; «al día / con deuda / morosa» es del reporte. Para el listado de unidades el grupo útil
en la gestión es la ocupación (¿qué unidad aún no tiene residente?). **Aprobado por Walther:** `ocupacion` en lugar de inventar un estado.
Proveedores no recibe chips (el Issue solo pide corregir su desborde).

**2. Validación: lista blanca, nunca error.** Un helper `leer_opcion(request, nombre, validos)` en `apps/core/listados.py` devuelve el valor o `""`.
No se usa un `Form` para `situacion` porque `FiltroReporteForm` invalida el reporte entero ante un valor malo; aquí un valor desconocido se ignora
(chip «Todos»). `situacion` se lee fuera del formulario; el mapa `clave → texto de FilaReporte.situacion` vive en un solo lugar
(`apps/gastos/filtros.py`, módulo nuevo, sin tocar `reportes.py`) y lo usan el reporte, el CSV y `InicioView`.

**3. Conteo de chips sin una consulta por estado.** Siempre sobre el queryset ya acotado por condominio y rol, **antes** de aplicar el filtro, con una sola consulta:
- Incidentes: `self.get_queryset()` de `IncidentesVisiblesMixin` (el residente cuenta solo los suyos) y `values("estado").annotate(n=Count("pk"))`.
- Egresos: `self.object.egresos` (el período ya sale de `CondominioQuerysetMixin`); `values("categoria").annotate(n=Count("pk"), subtotal=Sum("monto"))` reutiliza la consulta que hoy calcula el subtotal por categoría.
- Unidades: `Unidad.objects.filter(edificio__in=<queryset de la vista>)` con `aggregate(con=Count("pk", filter=Q(residentes__activo=True), distinct=True), total=Count("pk", distinct=True))`; se cuenta por unidad distinta para no duplicar por residente.
  Criterio de residencia: el mismo del panel de inicio («Residentes · Con residencia vigente») y de los residentes que muestra la lista, es decir `Residente.activo=True`. Se verificó en el código que el panel (`InicioView`) no compara `desde`/`hasta` con la fecha de hoy: el contrato C2 (`cobros_visibles`) filtra cobros por período, no unidades. Dar de baja marca `activo=False` y completa `hasta`. Una prueba de igualdad exige que «Con residentes» sume lo mismo que el panel.
- Reporte: `Counter(f.situacion for f in reporte.filas)` en memoria, como #79; ya respeta período y edificio y es independiente de `situacion` y de `solo_deuda`.

Nunca `Modelo.objects.all()`. Prueba con `assertNumQueries` por listado.

**4. Filtros, paginación y otros parámetros.** Un `FiltrosGetMixin` para `ListView` declara `parametros_filtro = ("estado", "q")` y arma en el contexto
`filtros_url` (los parámetros **válidos** de la URL, sin `page`) y `hay_filtros`. `_paginacion.html` no cambia: sigue leyendo `filtros_url`, ahora
armado para todos. La URL de cada chip conserva los demás parámetros (también los que no son filtros, como `periodo` o `edificio` del reporte),
reemplaza el suyo y elimina `page`. «Limpiar filtros» quita solo los parámetros de filtro y `page`, y conserva `periodo` y `edificio` del reporte.
El reporte (un `TemplateView`) usa las mismas funciones sobre `request.GET`.
Interacción con `solo_deuda`: si hay `situacion` válida, manda `situacion`; `solo_deuda` sigue funcionando cuando no hay chip.
**Aprobado por Walther** (alternativa descartada: intersectarlos, lo que deja «Al día» + «solo deuda» vacío).

**5. Orden por urgencia (primero lo que requiere acción) y desempate.**
- Incidentes: `RECIBIDO` (nadie lo ha tomado) → `EN_PROCESO` → `RESUELTO`. Se ordena con `Case/When` (rango 0, 1, 2); dentro de los abiertos el **más antiguo** primero (lleva más tiempo esperando) y entre los resueltos el **más reciente**. Desempate final por `-pk`. Sin migración.
- Reporte: `morosa` → `pendiente` → `al día`; dentro de cada grupo, mayor `deuda_total` primero y desempate por el orden actual de la unidad (el orden de Python es estable). Solo la página: el CSV conserva su orden por edificio y unidad, pero sí respeta `situacion`.
- Egresos: no tienen urgencia y **conservan su orden actual** (`fecha`, `pk`, del más antiguo al más reciente). **Rechazado por Walther** invertirlo.
- Unidades: sin cambio (edificio, piso, número); es un inventario y reordenarlo por ocupación rompería la lectura por edificio.

**6. Componente de chips: `templates/_chips.html`.** Recibe `chips` (lista de diccionarios `{valor, texto, cantidad, singular, plural, url, activo, clave_color}`) y `etiqueta` para el `aria-label`;
lo arma `apps/core/listados.py::armar_chips(...)` para que las vistas no repitan la lógica. Marcado: `<nav aria-label="Filtrar por estado">` con una lista de enlaces
`.chip`; el activo lleva `aria-current="true"`; la cantidad va visible con un `<span class="visually-hidden">12 incidentes</span>` y el número `aria-hidden`
para no leerlo dos veces. Los colores usan `--estado-*` (acento en el punto y el borde; `-fondo` y `-texto` en el chip activo): `al_dia`→`al-dia`, `pendiente`→`con-deuda`,
`morosa`→`moroso`, `RECIBIDO`→`recibido`, `EN_PROCESO`→`en-proceso`, `RESUELTO`→`resuelto`; «Todos», categorías y ocupación usan el neutro `--estado-reserva`. Foco visible
como en `.kpi`. Cada chip es un enlace GET, así que funciona sin JavaScript. «Limpiar filtros» va aparte, como enlace de texto.

**7. Insignias `.insignia-*` reemplazan a `.badge text-bg-*` en tres plantillas** (`incidentes/_estado.html`, `gastos/_estado.html`, `gastos/_situacion.html`):
`.insignia` (base: borde de 1 px con el acento, fondo `-fondo`, texto `-texto`, con la forma de `.badge`) más `.insignia-<estado>`. Se agrega `--estado-resuelto*` como alias de `al-dia` (mismos pares ya validados).
Período: Abierto→`en-proceso`, Emitido→`al-dia`. Contraste: los pares texto/fondo de #79 ya miden entre 6,72 y 10,86:1; la tarea de verificación recalcula cada par
con la fórmula WCAG y confirma ≥4,5:1 el texto y ≥3:1 el borde sobre su fondo. Las insignias Activo/Inactivo de proveedores quedan como están (no son estados de listado de #80).

**8. Tarjetas del panel.** `_tarjetas_de_unidades` suma `&situacion=<clave>` usando el mapa de `apps/gastos/filtros.py` (`al_dia`, `pendiente`, `morosa`) y se quita el `TODO(#80)`.
Como los chips cuentan la misma `situacion` que la tarjeta, las cantidades coinciden (prueba de igualdad).

**9. Desborde de `/proveedores/` a 375 px.** Causa: `.table-responsive` tiene `overflow-x: auto`, pero no es el bloque de contención de los elementos `position: absolute`;
el `span.visually-hidden` de la columna «Acciones» (`position: absolute` en Bootstrap) se ubica respecto de un ancestro mayor y aporta el ancho de 576 px al documento.
Corrección: `.table-responsive { position: relative; }` una sola vez en `condohub.css` (en vez de la clase utilitaria en cada plantilla), porque el mismo patrón (un `visually-hidden` en el `<th>` de
acciones dentro de `.table-responsive`) aparece en `periodo_detalle`, `pagos/cobranza`, `cuenta_unidad`, `estado_cuenta`, `reservas/mis_reservas` y `reservas/todas`.
La verificación mide `document.documentElement.scrollWidth` a 375 px en cada una de esas páginas y confirma que ninguna supera el ancho de la pantalla.

**10. Preparado para #82.** El nombre `q` queda reservado en `parametros_filtro` (se conserva en los enlaces de chips y de paginación, hoy sin efecto);
`hay_filtros` lo contará cuando exista y «Limpiar filtros» ya lo quitará. #82 solo agrega la condición `Q(...)` sobre el queryset de la vista y el endpoint; no vuelve a tocar chips ni paginación.
La búsqueda NO se implementa aquí.

## Risks / Trade-offs

- Cambio transversal: toca carpetas de Winderson (incidentes) y Maximiliano (condominios); se les avisa al unir.
- Chips de unidades por ocupación es una decisión de producto (el Issue habla de «estado»); aprobada.
- `.table-responsive { position: relative; }` es global: si otra tabla dependiera del comportamiento anterior, la medición a 375 px lo detecta.
