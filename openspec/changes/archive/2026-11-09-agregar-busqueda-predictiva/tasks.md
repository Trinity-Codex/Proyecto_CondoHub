# Tasks

## 1. Regla de búsqueda (servidor)

- [x] 1.1 Crear `apps/condominios/busqueda.py` con `normalizar_busqueda(texto)` (strip, 100 caracteres, hasta 5 palabras), `ver_rut(request)` y `filtrar_unidades(unidades, texto, *, ver_rut)` según la Decisión 2 del diseño (palabras con AND; número, nombre y apellido de residentes activos con `Exists`; prefijo del RUT sin guion solo con `ver_rut`), reutilizando `normalizar_rut`; verificar con pruebas en `apps/condominios/tests.py`: número, nombre en cualquier orden, RUT «12.345.678-5», «123456785» y «12345» para el administrador, el mismo RUT sin coincidencia para el comité, residente dado de baja excluido, texto vacío o con espacios sin filtro y unidad con dos residentes que no se duplica. Solo datos ficticios.
- [x] 1.2 Agregar la prueba de tildes («perez» encuentra «Pérez», «PÉREZ» encuentra «perez») con `skipUnless(connection.vendor == "mysql")` y verificar que corre en la CI (MySQL) y se salta con `USE_SQLITE=1`.

## 2. Listado con `?q=`

- [x] 2.1 En `apps/core/listados.py`, agregar `busqueda = False` a `FiltrosGetMixin`, el método `texto_busqueda()` (no puede llamarse igual que el atributo) y el argumento `busqueda=False` en `hay_filtros`, y actualizar la documentación del módulo (ya no «reservado»); verificar con pruebas que un listado sin búsqueda (incidentes con `?q=x`) no muestra «Limpiar filtros» y que con búsqueda sí, y que `url_limpiar` sigue quitando `q`.
- [x] 2.2 Extraer `UnidadesAccesoMixin` (roles administrador y comité, `model = Edificio`) y aplicar `filtrar_unidades` en `UnidadesView`: en el `Prefetch` de unidades junto con `ocupacion`, y en el conteo de chips (dentro de la búsqueda y antes de `ocupacion`); verificar con pruebas de `?q=` combinado con `?ocupacion=`, chips que cuentan dentro del resultado, aislamiento (unidad «504» y «Ana Pérez» ficticias en otro condominio: 0 coincidencias) y 403 para conserje y residente con `?q=`, y `assertNumQueries` sin consultas por unidad.
- [x] 2.3 Agregar el formulario GET (`role="search"`, `<label for>`, ayuda por rol enlazada con `aria-describedby`, `maxlength="100"`, `ocupacion` oculto si hay chip, botón «Buscar», región `aria-live="polite"` vacía y `data-busqueda` con la URL del endpoint) en `condominios/unidades.html`; verificar con una prueba que la página contiene el campo con el valor de `q`, que la ayuda del comité no menciona el RUT y que el HTML del comité con `?q=` no contiene ningún RUT.

## 3. Endpoint de sugerencias

- [x] 3.1 Crear `SugerenciasUnidadesView(UnidadesAccesoMixin, CondominioQuerysetMixin, ListView)` con `http_method_names = ["get"]`, respuesta JSON de la Decisión 4 (hasta 10, `hay_mas`, `rut` con `formatear_rut` solo si `ver_rut`, sin ids), lista vacía con menos de 2 caracteres y `add_never_cache_headers`, y la URL `unidades/sugerencias/` (`condominios:unidades_sugerencias`); verificar con pruebas: claves exactas del JSON para administrador y comité (sin `rut`), `Cache-Control` con `no-store`, «P» y «» vacíos sin consultas (`assertNumQueries(0)` tras el control de acceso), 15 coincidencias → 10 en orden y `hay_mas`, otro condominio → 0, conserje y residente → 403, POST → 405 y sin sesión → redirección al inicio de sesión.

## 4. JavaScript y estilos

- [x] 4.1 Crear `static/js/busqueda.js` (IIFE ES5, activado por `[data-busqueda]`) con el combobox de la Decisión 7: atributos ARIA, espera de 250 ms, `AbortController` y número de secuencia, flechas, Enter con y sin opción activa, Escape en dos pasos, Tab y clic, anuncios en `aria-live` y armado con `textContent`; cargarlo con `defer` en `templates/base.html` después de `formato.js`; verificar en el navegador (servidor de desarrollo con datos demo) cada escenario de «Búsqueda predictiva accesible» con el teclado, revisando `aria-expanded`, `aria-activedescendant` y `aria-selected` con `read_page`, y que una respuesta lenta de «Pé» no pisa a «Pér» (simulando la demora).
- [x] 4.2 Agregar `.busqueda`, `.busqueda-lista` y `.busqueda-opcion` en `static/css/condohub.css` (Decisión 8); verificar el contraste ≥ 4,5:1 de la opción activa con la fórmula WCAG y, midiendo rectángulos del DOM, que la lista abierta a 375 px y a 1440 px no supera el ancho de la pantalla ni tapa el botón «Buscar».
- [x] 4.3 Verificar sin JavaScript (desactivado en el navegador) que escribir «504» y presionar Enter filtra el listado, que el comité nunca recibe ni ve un RUT en la página ni en el JSON, y que el lector de pantalla del sistema anuncia la cantidad de sugerencias.

## 5. Demo, documentación y cierre

- [x] 5.1 Revisar `apps/condominios/demo.py`: si ningún residente demo tiene tilde en el nombre ni dos unidades con números parecidos, agregar uno ficticio para que la búsqueda se luzca en la demo; verificar con `python manage.py cargar_demo` y una búsqueda «perez».
- [x] 5.2 Anotar en `docs/GUIA_NUEVA_FEATURE.md` (o donde #80 documentó los filtros) cómo declarar `busqueda = True` y reutilizar `busqueda.js` en otro listado; verificar que el ejemplo coincide con el código.
- [x] 5.3 Correr `python manage.py makemigrations --check` (sin migraciones), `python manage.py test apps` completo y `openspec validate agregar-busqueda-predictiva --strict`; los tres en verde.

## Workflow follow-up

- `/code-review high` sobre el diff (nivel A: endpoint con datos personales), con foco en aislamiento por condominio y por rol.
- Archivar el cambio en el mismo PR antes de unirlo (`/opsx:archive`) y avisar a Maximiliano que `apps/condominios` cambió.
