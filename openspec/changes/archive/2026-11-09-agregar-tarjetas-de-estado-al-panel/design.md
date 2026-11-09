# Design

## Context

`InicioView` (`apps/core/views.py`) arma hoy un `resumen` con cuatro conteos para administrador, comité y conserje
y, solo para administrador y comité, `cobranza = generar_reporte(último período emitido)` (#57). La plantilla
pinta `.tarjeta-indicador` (borde izquierdo por posición con `nth-child`) y una tarjeta de cobranza con tres
cifras. Los incidentes ya se filtran con `?estado=` en `incidentes:lista`; reservas y unidades no filtran por GET.
Las reservas solo tienen los estados CONFIRMADA y CANCELADA (no existe «pendiente»).

## Goals / Non-Goals

**Goals:** tarjetas por estado con enlace entero; cantidades correctas y del condominio activo; paleta AA reutilizable
por #80; sin consultas pesadas nuevas ni más datos visibles que hoy para ningún rol.

**Non-Goals:** implementar filtros en listados (#80), insignias, panel del residente, nuevos estados de reserva.

## Decisions

**1. Tarjetas por rol (nadie ve más que hoy).**
- Administrador y comité (hoy ven resumen y cobranza): 6 tarjetas: al día, con deuda, morosas, incidentes
  recibidos, incidentes en proceso y reservas próximas.
- Conserje (hoy ve el resumen, sin dinero): 3 tarjetas: incidentes recibidos, en proceso y reservas próximas. Sin las
  de unidades, porque salen de la cobranza y esta contiene dinero.
- Residente: sin cambios (ya tiene sus propias tarjetas).
- Sin período emitido: las tarjetas de unidades no se muestran; sigue el aviso actual de #57.

**2. Unidades desde el reporte de #57, con cero consultas nuevas.** `cobranza` ya trae `filas`; cada `FilaReporte`
tiene `situacion` / `es_morosa`. Las tres cifras particionan las unidades del período: *morosas* =
`len(unidades_morosas)`; *con deuda* = `len(unidades_con_deuda) - len(unidades_morosas)` (debe solo el mes, el
«Pendiente» del reporte); *al día* = `len(filas) - len(unidades_con_deuda)`. La regla de morosidad sigue solo en
`apps/gastos/reportes.py`; la vista no la repite. Suman las unidades del período y coinciden con el reporte.
Las frases nombran el período («Del período Octubre 2026»), porque «al día» es relativo a él.

**3. Incidentes y reservas con una consulta cada uno.** Un `values("estado").annotate(Count)` sobre los incidentes
del condominio reemplaza el `count()` actual de abiertos: recibidos = RECIBIDO, en proceso = EN_PROCESO (RESUELTO no
se muestra). Un `count()` de reservas CONFIRMADAS desde hoy (mismo criterio que `ReservaListView`) reemplaza
«Reservas hoy»; la frase indica cuántas son hoy, para no perder el dato. Como el Issue pide «reservas pendientes»
y ese estado no existe, se propone «reservas próximas»: **decisión a aprobar**.

**4. Qué pasa con lo actual (sin perder información).**
- «Incidentes abiertos» y «Reservas hoy» del resumen pasan a las tarjetas (lo de hoy va en la frase de reservas).
- «Unidades» y «Residentes» quedan como dos `.tarjeta-indicador` informativas, sin enlace, bajo el título «Resumen».
- La tarjeta de cobranza se mantiene con recaudación y deuda total (dinero) y su enlace «Ver reporte»; su
  tercera cifra, unidades morosas, pasa a la tarjeta morosa: el mismo número en dos lugares confunde. Por eso se
  modifica el requisito «Indicadores de cobranza» de `reportes`.
- El borde por `nth-child` de `.tarjeta-indicador` se reemplaza por una clase explícita, para no depender del orden.

**5. Destinos de los enlaces.**

| Tarjeta | URL | Estado |
|---|---|---|
| Incidentes recibidos / en proceso | `incidentes:lista?estado=RECIBIDO` / `EN_PROCESO` | ya filtra |
| Reservas próximas | `reservas:todas` | la lista ya es «desde hoy, confirmadas» |
| Unidades al día / con deuda / morosas | `gastos:reporte?periodo=<pk>` | sin filtro hoy |

Contrato para #80: `?situacion=al_dia|pendiente|morosa` sobre el reporte de recaudación (valores iguales a
`FilaReporte.situacion`). Hasta entonces el enlace va sin ese parámetro; la vista arma los enlaces en un solo
lugar, así que sumarlo es una línea. El reporte no figura entre las carpetas de #80: **decisión a aprobar** si
#80 lo incluye o si los enlaces de unidades quedan sin filtro en el PMV.

**6. Paleta por estado (variables en `condohub.css`).** Cada estado define `--estado-X` (borde y punto),
`--estado-X-fondo` y `--estado-X-texto` (para las insignias de #80). La cantidad y el nombre van en azul marino o
texto oscuro, nunca en el color de acento.

| Estado | Acento (contraste sobre blanco) | Texto / fondo suave (contraste) |
|---|---|---|
| al día | `#4f8a1e` (4,21) | `#2e5a0f` / `#e9f5de` (7,19) |
| con deuda | `#c55a12` (4,33) | `#8a3d08` / `#fdeee2` (6,72) |
| moroso | `#b42318` (6,57) | `#8f1d14` / `#fdeceb` (7,81) |
| recibido | `#113358` (12,82) | `#113358` / `#e6edf5` (10,86) |
| en proceso | `#0d7a7f` (5,11) | `#0a5b5f` / `#e2f4f5` (6,91) |
| reserva | `#5c6b7a` (5,47) | `#2f3b47` / `#eef1f4` (10,08) |

Mínimos: 3:1 para el acento (elemento gráfico) y 4,5:1 para texto; todos los pares los superan, calculados con la
fórmula WCAG 2.x (sobre el fondo de página `#f4f7f9` el menor acento es 3,91). El color nunca va solo: cada tarjeta
lleva el nombre del estado y la cantidad.

**7. Grilla y accesibilidad.** `row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xxl-6 g-3`: una columna a 375 px,
dos desde sm, tres desde lg y seis en una fila a 1440 px (contenedor de 1320 px, unos 205 px por tarjeta; el conserje,
con tres, usa `row-cols-xxl-3`). Cada tarjeta es un solo `<a class="kpi">` con nombre visible, cantidad y frase:
su nombre accesible sale del texto («Morosas, 4 unidades»). El punto de color es `aria-hidden`. Foco con
`:focus-visible`: anillo de 3 px con 2 px de separación. Sin `title` ni `aria-label` redundantes. La verificación
mide rectángulos del DOM (solapes, `scrollWidth > clientWidth`, desborde horizontal) a 375 y 1440 px.

**8. Textos en la vista.** `InicioView` entrega `tarjetas`: lista de diccionarios `{clave, nombre, cantidad, frase,
url}` (la clave elige `.kpi-<clave>`); la plantilla solo la recorre. El singular y el plural («1 unidad», «4 unidades»)
se resuelven en la vista.

## Risks / Trade-offs

- El panel es de Maximiliano: es un cambio transversal y se le avisa al unir.
- Si #80 no filtra el reporte, tres tarjetas llevan a una página sin filtro; el contrato queda escrito.
- Naranjo y rojo conviven en el sitio con otros usos (avisos); el texto de cada tarjeta es lo que las distingue.
