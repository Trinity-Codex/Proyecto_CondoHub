# Design

## Context

- `UnidadesView(FiltrosGetMixin, RolRequeridoMixin, CondominioQuerysetMixin, ListView)` lista `Edificio` del condominio activo
  (sin paginar), con `Prefetch` de unidades (filtradas por `?ocupacion=`) y de residentes con `activo=True`. Roles: administrador
  y comité. La plantilla muestra el RUT del residente solo `{% if es_admin %}` (#77); el comité ve nombre, tipo y fecha de inicio.
- Criterio de residencia (#80): `Residente.activo=True`, el mismo del panel y de los chips de ocupación (`_con_residente_activo`).
- `Usuario`: `first_name`, `last_name`, `rut` guardado normalizado (`12345678-5`, `normalizar_rut`); `__str__` = nombre completo o correo.
- `apps/core/listados.py` reserva `q`: los chips y la paginación lo conservan y `url_limpiar` lo quita, pero `hay_filtros` no lo cuenta.
- Base de datos: `docs/crear_base_datos.sql` crea la base con `utf8mb4_unicode_ci` y el MySQL 8 de la CI usa `utf8mb4_0900_ai_ci`
  por defecto; ambas collations ignoran mayúsculas y tildes en `LIKE`. SQLite (`USE_SQLITE=1`) solo ignora mayúsculas ASCII.
- No hay `CACHES` configurado (caché local por proceso). #52 limita intentos de inicio de sesión con una tabla (`IntentoFallido`),
  pensado para credenciales. `apps/privacidad/views.py` ya usa `add_never_cache_headers` para datos personales.
- `static/js/formato.js` es una IIFE en ES5, sin npm, cargada con `defer` desde `base.html` y activada por atributos `data-*`.

## Goals / Non-Goals

**Goals:** una sola regla de búsqueda para el listado y las sugerencias, que nunca muestre a un rol más de lo que ya ve;
combobox accesible y progresivo; sin migraciones ni dependencias.
**Non-Goals:** búsqueda en otros listados (el módulo queda reutilizable, pero no se conecta), resaltar coincidencias, búsqueda
difusa o por similitud, búsqueda de texto completo de MySQL.

## Decisions

**1. Quién busca y qué ve cada rol (decisión de privacidad; a aprobar por Walther).** Los mismos roles del listado: administrador
y comité (`roles_permitidos = [ADMINISTRADOR, COMITE]` en un `UnidadesAccesoMixin` que comparten las dos vistas, para que no
puedan diferir). Conserje y residente reciben 403 en el listado y en el endpoint.
- **Administrador:** busca por número, nombre, apellido y RUT; las sugerencias traen el RUT con puntos.
- **Comité:** busca por número, nombre y apellido. El RUT **no entra en la condición de búsqueda** (no basta con ocultarlo en la
  respuesta: si filtrara por RUT, la aparición o no de una unidad revelaría el RUT por prueba y error). Las sugerencias no traen RUT.
- La decisión se toma con `tiene_rol(request, ADMINISTRADOR)`, igual que `es_admin` en la plantilla, dentro de una sola función
  (`ver_rut`) que usan el listado y el endpoint. El superusuario actúa como administrador (`roles_en`).
- Alternativa descartada: dejar al comité buscar por RUT sin mostrarlo. Filtra el dato igual (ataque de deducción).

**2. Qué se busca y cómo: `apps/condominios/busqueda.py`.** Una función pura sobre querysets, sin request:
`filtrar_unidades(unidades, texto, *, ver_rut)` → queryset. La usan `UnidadesView` (dentro del `Prefetch` de unidades y en el conteo
de chips) y el endpoint, siempre sobre `Unidad.objects.filter(edificio__in=<edificios de CondominioQuerysetMixin>)`. Nunca `Modelo.objects.all()`.
- **Normalización del texto:** `strip`, se corta a 100 caracteres y se divide por espacios en a lo más 5 palabras (las demás se ignoran).
- **Cada palabra (AND)** debe coincidir con **alguna** de (OR): `numero__icontains`, o `Exists(Residente activo de esa unidad cuyo
  usuario tiene first_name__icontains o last_name__icontains)`, y solo con `ver_rut`, el RUT: si la palabra, sin puntos, espacios ni
  guion y en mayúsculas, son solo dígitos con una K final opcional, se compara con `istartswith` contra el RUT sin guion
  (`Replace("usuario__rut", Value("-"), Value(""))`). Así «12.345.678-5», «123456785» y «12345» encuentran `12345678-5`.
  Se reutiliza `normalizar_rut` de `apps/core/formato.py` y solo se le quita además el guion.
- **Por qué prefijo para el RUT** y no `icontains`: las personas escriben el RUT desde el inicio; `contains` con «12» coincidiría con casi
  todos. **Por qué palabras con AND:** «perez ana» y «ana perez» encuentran a la misma persona sin concatenar columnas.
- **Por qué `Exists` y no un `join`:** no duplica unidades con varios residentes y no necesita `distinct()`.
- **Mayúsculas y tildes:** las da la collation `_ci`/`_ai_ci` de MySQL; no se agrega `unaccent` ni se normaliza en Python. La prueba de
  tildes («perez» → «Pérez») se salta en SQLite con `skipUnless(connection.vendor == "mysql")`; la CI corre en MySQL.
- **Residentes que cuentan:** `activo=True` (decisión 3 de #80). Un residente dado de baja no hace aparecer su antigua unidad.
- **No se busca por correo,** aunque el listado lo muestra cuando el usuario no tiene nombre: el Issue no lo pide y amplía la superficie.
- **Rendimiento:** `LIKE '%x%'` no usa índice, pero recorre solo las unidades de un condominio (decenas a cientos) con a lo más 5 palabras
  × 3 o 4 columnas. El endpoint corta a 11 filas (`[:11]` para saber si hay más). Se prueba con `assertNumQueries`. **No se propone índice
  ni migración:** un índice B-tree no ayuda a `%x%` y uno FULLTEXT de MySQL no busca por prefijo de RUT ni existe en SQLite.

**3. El listado con `?q=`.** `FiltrosGetMixin` suma un atributo `busqueda = False`; con `busqueda = True`, `self.texto_busqueda()` devuelve
el texto normalizado y `hay_filtros` lo cuenta. `hay_filtros(get, parametros_filtro, busqueda=False)` gana un argumento con valor por
defecto, así los demás listados (que no declaran búsqueda) no cambian: un `?q=` en incidentes sigue sin efecto y sin «Limpiar filtros».
- `UnidadesView` aplica `filtrar_unidades` en el `Prefetch` (como `ocupacion`) y en el conteo de los chips: **los chips cuentan dentro
  del resultado de la búsqueda y antes de `ocupacion`** (la cantidad dice cuántas de las encontradas tienen o no residentes).
- El listado filtra desde **1 carácter** (Enter es una acción deliberada y hay unidades «1» o «A»); el endpoint, desde 2 (Decisión 4).
- Los edificios sin coincidencias se siguen mostrando con «Ninguna unidad con este filtro.», igual que con `ocupacion` en #80.
- No hay paginación en Unidades; `filtros_url` y los chips ya conservan `q` (#80), por lo que no se toca `_paginacion.html` ni `_chips.html`.
- Formulario: `<form method="get" role="search">` sobre los chips, con `<label for>` visible «Buscar unidad o residente», `<input type="search"
  name="q" maxlength="100">` con el valor actual, un `<input type="hidden" name="ocupacion">` si hay chip activo y un botón «Buscar».
  Ayuda enlazada por `aria-describedby`: «Número de unidad, nombre o RUT.» para el administrador y «Número de unidad o nombre.» para el
  comité; placeholder ficticio («Ej.: 504 o Ana Pérez»). Con `q`, el título de la tabla vacía dice «Ninguna unidad con este filtro.».

**4. El endpoint JSON.** `SugerenciasUnidadesView(UnidadesAccesoMixin, CondominioQuerysetMixin, ListView)`, con `model = Edificio`
(el mismo queryset de partida del listado) y `render_to_response` que devuelve `JsonResponse`.
- URL: `GET /condominio/unidades/sugerencias/?q=…`, nombre `condominios:unidades_sugerencias`. `http_method_names = ["get"]` → POST 405.
- Respuesta: `{"resultados": [{"edificio": "Torre A", "unidad": "101", "residentes": [{"nombre": "Ana Pérez", "rut": "12.345.678-5"}]}],
  "hay_mas": false}`. `nombre` es `str(usuario)` (lo mismo que muestra el listado), `rut` sale con `formatear_rut` **y la clave no existe**
  para el comité. Sin `pk` ni ids: la sugerencia elegida se resuelve en el listado por `q` (Decisión 7). Hasta 10 unidades, en el orden
  del listado (edificio, piso, número), con todos sus residentes activos (como el listado).
- Texto normalizado de menos de 2 caracteres → `{"resultados": [], "hay_mas": false}` sin consultar unidades.
- Sin sesión o sin condominio activo: el mismo comportamiento de `RolRequeridoMixin` (redirige); el JS trata una respuesta que no es JSON
  como error. Rol sin acceso: 403 (`PermissionDenied`).
- Caché: `add_never_cache_headers` (como la descarga de datos de `privacidad`): `Cache-Control: max-age=0, no-cache, no-store,
  must-revalidate, private`. Alternativa descartada: `@never_cache` en la URL; se prefiere el mismo estilo que `privacidad`.

**5. Abuso: sin límite de frecuencia en el PMV (a aprobar por Walther).** Solo llegan personas con sesión y con rol administrador o
comité del condominio, y el endpoint no expone nada que el listado no muestre ya completo a ese rol en una sola página: limitar las
sugerencias no protege datos que `/condominio/unidades/` entrega de una vez. La carga por persona la acotan la espera de 250 ms, la
cancelación de solicitudes y el tope de 10 filas. El patrón de #52 (tabla en la base) es para credenciales y escribir una fila por
tecla sería más caro que la búsqueda. Si en el futuro se abre a residentes o conserjes, se revisa.

**6. Auditoría y privacidad: no se registran las búsquedas (a aprobar por Walther).** `apps.auditoria.servicios.registrar` (C1) registra
**cambios** (`Accion` = crear, modificar, anular, eliminar, cambiar rol) y la regla del proyecto pide auditoría cuando un cambio *toca*
datos personales; buscar es leer lo que el listado ya muestra, que tampoco se registra. Guardar los textos buscados sería además
**crear** datos personales nuevos (RUT y nombres tecleados) contra el principio de minimización de la Ley 21.719. Por lo mismo, el
endpoint no escribe `q` en logs propios. Alternativa descartada: agregar `Accion.CONSULTAR`; obliga a decidir retención y acceso a ese
registro, fuera del alcance de un Could. No hace falta cambiar el aviso de privacidad: no hay dato ni finalidad nuevos.

**7. `static/js/busqueda.js`.** IIFE en ES5 como `formato.js`, sin npm, sin mezclarse con él; se carga con `defer` en `base.html`
y no hace nada si la página no tiene `[data-busqueda]`. El atributo lleva la URL del endpoint: `data-busqueda="{% url … %}"`.
- **Marcado que agrega el JS** (sin JS el campo es un `type="search"` normal): en el input, `role="combobox"`, `aria-autocomplete="list"`,
  `aria-expanded="false"`, `aria-controls` y `autocomplete="off"`; un `<ul role="listbox">` hermano con `aria-label`, y cada sugerencia
  `<li role="option" id="…-opcion-N" aria-selected>`. La región `aria-live="polite"` (`.visually-hidden`) ya está en la plantilla desde la
  carga, para que los lectores la registren antes del primer anuncio.
- **Espera y cancelación:** 250 ms desde la última tecla; cada solicitud nueva llama `abort()` sobre el `AbortController` anterior y además
  se compara un número de secuencia antes de pintar (por si el navegador entrega una respuesta ya resuelta). Menos de 2 caracteres: se cierra
  la lista sin pedir nada. `fetch` con `credentials: "same-origin"` y `Accept: application/json`.
- **Teclado:** ↓ abre o baja, ↑ sube (sin dar la vuelta), Inicio y Fin quedan para mover el cursor del texto (APG). La opción activa se
  marca con `aria-activedescendant` y `aria-selected="true"`; el foco nunca sale del input. **Enter con opción activa:** pone en `q` el
  número de esa unidad y envía el formulario (conserva `ocupacion`); **Enter sin opción activa:** envío normal del formulario con lo escrito.
  **Escape:** con la lista abierta la cierra; cerrada, borra el texto (APG). Tab y la pérdida de foco cierran la lista. Clic en una opción =
  Enter sobre ella (`mousedown` con `preventDefault` para no perder el foco).
- **Anuncios** (`aria-live`): «3 sugerencias. Use las flechas para elegir.», «10 sugerencias; hay más, presione Enter para ver todas.»,
  «Sin resultados.», «No se pudieron cargar las sugerencias.». No se anuncia nada con menos de 2 caracteres.
- **Cada sugerencia**: primera línea «Torre A · Unidad 101»; segunda, los residentes separados por coma: «Ana Pérez (12.345.678-5)» si viene
  `rut`, solo «Ana Pérez» si no; «Sin residentes» si la lista está vacía. Todo con `textContent` y `createElement`, nunca `innerHTML`.
  El JS no decide qué ver: muestra lo que trae el JSON, y el servidor decide por rol.

**8. CSS en `condohub.css`.** `.busqueda` (`position: relative`), `.busqueda-lista` (absoluta bajo el campo, ancho del campo, `max-height`
con desplazamiento, borde y sombra de Bootstrap) y `.busqueda-opcion[aria-selected="true"]` con fondo y texto de la paleta de #79 con
contraste ≥ 4,5:1 y un borde izquierdo como indicador que no depende solo del color. A 375 px la lista no supera el ancho de la pantalla.

## Risks / Trade-offs

- [Riesgo] Una nueva vista o plantilla que muestre el RUT al comité por error. → `ver_rut` está en una sola función; pruebas para el
  comité en el listado y el endpoint: ningún `rut` en el JSON, ninguna coincidencia por RUT y ningún «12.345.678-5» en el HTML.
- [Riesgo] Sin límite de frecuencia, un script con sesión de administrador puede consultar mucho. → Igual podría descargar el listado
  completo; el tope de 10 filas y la consulta acotada al condominio limitan el costo. Se revisa si el endpoint se abre a más roles.
- [Riesgo] Las tildes no se ignoran en SQLite. → Solo afecta el modo de prueba rápida; la base real y la CI usan MySQL. Prueba marcada.
- [Trade-off] Elegir una sugerencia filtra por `q=<número>`, lo que también muestra unidades de otros edificios con el mismo número o
  que lo contienen («101» y «1010»). Se prefiere a exponer ids; con pocos edificios el resultado sigue siendo corto.
- [Trade-off] Cambio transversal en la carpeta de Maximiliano (`apps/condominios`); se le avisa al unir.

## Migration Plan

Sin migraciones. Desplegar es unir el PR; deshacer es revertirlo. `collectstatic` publica `busqueda.js` como los demás estáticos.
