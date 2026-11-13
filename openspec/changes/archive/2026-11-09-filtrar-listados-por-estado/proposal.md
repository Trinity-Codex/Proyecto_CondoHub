Issue: #80 (`Closes #80`). MoSCoW: Could (UI-6 del reporte de mejoras de interfaz). Depende de #79 (unido: paleta `--estado-*`).
Fuera de alcance: la búsqueda `?q=` (#82, solo se reserva el nombre), listados de reservas, comunicados y pagos,
filtros de proveedores, `django-filter`, nuevos estados, la regla de morosidad y `generar_reporte`, y cualquier migración.

## Why

Los listados muestran todo mezclado: quien administra no ve de un vistazo cuántos incidentes esperan atención ni qué
unidades deben, y las tarjetas del panel (#79) llevan a páginas sin filtro. Además `/proveedores/` se desborda
horizontalmente a 375 px (576 px de ancho) y las etiquetas de estado usan colores de Bootstrap que no siguen la paleta
de CondoHub. Entrega PMV: 27 de noviembre de 2026.

## What Changes

- **Chips de estado con cantidad** sobre incidentes (`?estado=`), reporte de recaudación (`?situacion=al_dia|pendiente|morosa`),
  egresos del período (`?categoria=`) y unidades (`?ocupacion=con_residentes|sin_residentes`). Valor desconocido: se ignora.
- **«Limpiar filtros»** solo si hay alguno; chips y paginación conservan el resto de la URL.
- **Orden por urgencia**: incidentes (recibidos primero) y reporte (morosas primero); egresos y unidades conservan su orden natural.
- **Insignias `.insignia-*`** con `--estado-*-fondo` y `--estado-*-texto`, que reemplazan a `.badge` en los estados de incidentes, períodos y situación de unidad.
- **Panel**: las tarjetas de unidades enlazan con `?situacion=` (cierra el TODO de #79).
- **Corrección** del desborde de `/proveedores/` a 375 px y del mismo patrón en otras tablas.
- **Preparado para #82**: el parámetro `q` queda reservado y el mecanismo de filtros acepta sumar uno nuevo sin tocar la paginación.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: se agregan «Listados con chips de estado y filtros por GET», «Chips accesibles que conservan la URL», «Insignias de estado accesibles» y se modifica «Uso desde el celular».
- `incidentes`: se agrega «Filtro y orden de la lista de incidentes».
- `condominios`: se agrega «Filtro de unidades por ocupación».
- `gastos-comunes`: se agrega «Filtro de egresos por categoría».
- `reportes`: se agrega «Filtro del reporte por situación de la unidad».

## Impact

- **Código:** `apps/core` (helper de filtros, `InicioView`, plantilla `_chips.html`, CSS), vistas y plantillas de `incidentes`
  (Winderson), `condominios` (Maximiliano), `gastos` (Walther) y `proveedores`. Pruebas en el `tests.py` de cada app. Sin migraciones ni dependencias.
- **Otros integrantes:** cambio transversal; se avisa a Maximiliano y Winderson al unir.
- **Contrato C0 a C6:** no cambia ninguna firma; `_paginacion.html` conserva su contrato `filtros_url`.
