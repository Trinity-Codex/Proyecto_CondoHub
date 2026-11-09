## ADDED Requirements

### Requirement: Búsqueda predictiva accesible
Con JavaScript, un campo de búsqueda marcado para sugerencias SHALL comportarse como un combobox de ARIA 1.2: pide sugerencias desde 2 caracteres tras 250 ms sin escribir, se maneja con flechas, Enter y Escape, y anuncia la cantidad de resultados en `aria-live="polite"`. Una respuesta vieja MUST NOT reemplazar a una más nueva. Sin JavaScript SHALL ser un formulario GET que funciona igual. El texto de cada sugerencia MUST insertarse como texto, nunca como HTML.

#### Scenario: Sugerencias con el teclado
- **WHEN** el administrador escribe «Pér» en la búsqueda de Unidades y baja con la flecha
- **THEN** el campo tiene `aria-expanded="true"` y `aria-activedescendant` apunta a la primera opción, marcada con `aria-selected="true"`, y la región `aria-live` dice cuántas sugerencias hay

#### Scenario: Elegir una sugerencia
- **WHEN** la persona presiona Enter (o hace clic) sobre la sugerencia de la unidad 101 de la Torre A
- **THEN** el formulario se envía con `q` igual al número de esa unidad, conservando los demás filtros de la URL

#### Scenario: Enter sin sugerencia elegida
- **WHEN** la persona escribe «Torres» y presiona Enter sin elegir una opción
- **THEN** el formulario se envía con `q=Torres` y el listado se filtra en el servidor

#### Scenario: Escape
- **WHEN** la lista está abierta y la persona presiona Escape, o la lista está cerrada y vuelve a presionarlo
- **THEN** primero se cierra la lista (`aria-expanded="false"`) y luego se borra el texto, sin enviar el formulario

#### Scenario: Respuestas desordenadas
- **WHEN** la persona escribe «Pé» y luego «Pér», y la respuesta de «Pé» llega después
- **THEN** la lista muestra solo las sugerencias de «Pér»

#### Scenario: Sin resultados o con error
- **WHEN** no hay coincidencias o la solicitud falla
- **THEN** la región `aria-live` dice «Sin resultados.» o «No se pudieron cargar las sugerencias.», y Enter sigue enviando el formulario

#### Scenario: Sin JavaScript
- **WHEN** el navegador no ejecuta JavaScript y la persona escribe «504» y presiona Enter
- **THEN** el listado se filtra igual por `?q=504`

#### Scenario: Acceso por rol
- **WHEN** un residente abre la página de Unidades con la búsqueda
- **THEN** recibe 403, igual que sin búsqueda, y nunca ve el campo
