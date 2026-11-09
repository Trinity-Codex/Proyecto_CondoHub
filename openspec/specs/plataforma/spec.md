# plataforma Specification

## Purpose
Requisitos transversales de la aplicación: acceso desde el celular, instalación como PWA, respuestas de
error y protecciones generales (RNF02, RNF03, RNF06, RNF13). Código: `config/`, `templates/`, `static/`, `apps/core`.

## Requirements

### Requirement: Uso desde el celular
El sistema SHALL adaptar todas las páginas a pantallas desde 360 px, mostrando las tablas como tarjetas en el celular, sin desplazamiento horizontal de la página (el texto oculto para lectores dentro de una tabla desplazable MUST NOT ampliar el ancho), y SHALL poder instalarse como aplicación web (manifest e íconos).

#### Scenario: Tabla en el celular
- **WHEN** un residente abre Mi cuenta en una pantalla de 360 px
- **THEN** ve sus cobros sin desplazamiento horizontal

#### Scenario: Proveedores en el celular
- **WHEN** el administrador abre `/proveedores/` a 375 px
- **THEN** el ancho del documento no supera el de la pantalla

### Requirement: Respuestas sin permiso
El sistema SHALL responder 403 cuando el rol no permite una acción y 404 cuando el registro no pertenece al usuario o a su condominio.

#### Scenario: Acción no permitida
- **WHEN** un residente intenta registrar un pago
- **THEN** ve la página "No tienes permisos" (403)

### Requirement: Integridad ante solicitudes simultáneas
El sistema MUST evitar reservas dobles, cobros duplicados y pagos por más de lo adeudado cuando llegan solicitudes simultáneas, bloqueando las filas afectadas.

#### Scenario: Dos clics seguidos
- **WHEN** una persona presiona dos veces el botón de confirmar una operación
- **THEN** la operación se registra una sola vez

### Requirement: Protección de formularios
El sistema SHALL proteger todos los formularios contra falsificación de solicitudes (CSRF) y guardar las contraseñas solo como hash.

#### Scenario: Formulario sin token
- **WHEN** llega un envío de formulario sin token CSRF válido
- **THEN** el sistema lo rechaza

### Requirement: Formularios accesibles
El sistema SHALL dibujar todos los campos de formulario con un componente común que enlaza ayuda y error al control con `aria-describedby`, marca con `aria-invalid` solo los campos con error y usa un placeholder con contraste AA. Las listas desplegables SHALL mostrar «Seleccione…» en vez de `---------`. El componente MUST NOT cambiar los permisos ni el envío del formulario.

#### Scenario: Campo con error
- **WHEN** un formulario vuelve con un error en un campo que tiene ayuda
- **THEN** el control lleva `aria-invalid="true"`, la clase `is-invalid` y `aria-describedby` con los ids de la ayuda y del error

#### Scenario: Campo sin error
- **WHEN** un formulario se abre sin errores
- **THEN** ningún control lleva `aria-invalid` ni `is-invalid`

#### Scenario: Lista desplegable vacía
- **WHEN** un formulario muestra una lista desplegable sin valor elegido
- **THEN** la primera opción dice «Seleccione…», salvo que el formulario defina su propio texto (por ejemplo «Sin proveedor»)

#### Scenario: Casillas y botones de opción
- **WHEN** un formulario tiene una casilla o un grupo de botones de opción
- **THEN** la casilla usa `form-check` y el grupo va en un `fieldset` con `legend`

#### Scenario: Acceso por rol sin cambios
- **WHEN** un residente abre una página de formulario que su rol no permite
- **THEN** sigue viendo "No tienes permisos" (403), y quien sí tiene permiso ve la página con el componente nuevo (200)

### Requirement: Montos en pesos legibles
Los campos de dinero que escribe el usuario SHALL aceptar pesos enteros con o sin puntos de miles y signo `$`, mostrarlos con prefijo `$` y puntos, y guardar el mismo entero. MUST rechazar con un mensaje en español toda entrada que no sea un entero en pesos y MUST conservar los mínimos y máximos de cada campo. Todo SHALL funcionar sin JavaScript y MUST NOT cambiar los permisos ni el formato `$1.234.567` de los montos mostrados.

#### Scenario: Monto con puntos y signo
- **WHEN** el administrador registra un egreso escribiendo «$ 1.250.000»
- **THEN** el egreso se guarda con monto 1250000

#### Scenario: Monto sin puntos
- **WHEN** el administrador escribe «1250000» o « 85.000 » en un campo de dinero
- **THEN** se guardan 1250000 y 85000 respectivamente

#### Scenario: Monto ambiguo o inválido
- **WHEN** el usuario escribe «1,5», «1.5», «1.25.000», «0.500», «01.000», «-5» o «abc» en un campo de dinero
- **THEN** el formulario vuelve con un error en ese campo que explica que el monto va en pesos enteros, y no se guarda nada

#### Scenario: El JavaScript no cambia un monto sin avisar
- **WHEN** con JavaScript activo el usuario escribe «1500.5» o «1,5», o pega un texto que no es un monto válido, y sale del campo
- **THEN** el campo conserva exactamente lo escrito (sin reagrupar dígitos) y, al enviar, el servidor muestra el error

#### Scenario: Cero como monto
- **WHEN** el usuario escribe «0» en un egreso y en la tarifa de un espacio común
- **THEN** el egreso se rechaza y la tarifa se acepta con 0 (gratis)

#### Scenario: Monto sobre el máximo
- **WHEN** el administrador escribe un egreso de «1.000.000.000» (sobre el máximo de 999.999.999)
- **THEN** el egreso se rechaza como hasta ahora

#### Scenario: Formulario que vuelve con error
- **WHEN** un formulario con «1.250.000» en el monto vuelve por un error en otro campo
- **THEN** el campo de monto sigue mostrando «1.250.000»

#### Scenario: Editar un monto guardado
- **WHEN** el administrador abre la edición de un egreso de 450000 pesos
- **THEN** el campo muestra «450.000» con el prefijo `$`

#### Scenario: Sin JavaScript
- **WHEN** el navegador no ejecuta JavaScript y el administrador envía «1.250.000»
- **THEN** el monto se guarda igual que con JavaScript

#### Scenario: Montos mostrados sin cambios
- **WHEN** una tabla o un PDF muestra un monto de 1234567, uno negativo de -5000 o uno vacío
- **THEN** se ven «$1.234.567», «-$5.000» y «$0», igual que antes del cambio

#### Scenario: Acceso por rol sin cambios
- **WHEN** un residente intenta abrir el formulario de egreso, de registro de pago o de espacio común
- **THEN** recibe "No tienes permisos" (403), y el administrador del condominio ve el formulario con el campo de monto (200)

### Requirement: RUT legible en formularios y listados
Los campos de RUT SHALL aceptarlo con o sin puntos, guardarlo normalizado (`12345678-5`) y mostrarse con un ejemplo ficticio válido; los listados SHALL mostrarlo con puntos. Con JavaScript SHALL formatearse en vivo y avisar «RUT válido.» en `aria-live="polite"`, y MUST mostrar el error solo al salir del campo, sin cambiar dígitos sin avisar. Todo SHALL funcionar sin JavaScript, sin cambiar validación, permisos ni lo guardado.

#### Scenario: Mostrar con puntos
- **WHEN** un listado muestra los RUT guardados `12345678-5`, `1234567-4` y `96511790-K`
- **THEN** se ven «12.345.678-5», «1.234.567-4» y «96.511.790-K», y un texto que no es un RUT se ve igual que está guardado

#### Scenario: Guardar normalizado
- **WHEN** el administrador registra un proveedor o a un usuario escribiendo «12.345.678-5» o «12345678-5»
- **THEN** se guarda `12345678-5` en ambos casos

#### Scenario: RUT con K y de 7 dígitos
- **WHEN** se escribe «10.000.013-k» o «1.234.567-4»
- **THEN** ambos se aceptan y se guardan `10000013-K` y `1234567-4`

#### Scenario: Dígito verificador incorrecto
- **WHEN** se envía «12.345.678-9»
- **THEN** el formulario vuelve con «El dígito verificador del RUT no es correcto.» y no guarda

#### Scenario: Valor mostrado al volver con error
- **WHEN** un formulario con el RUT `12345678-5` vuelve por un error en otro campo, o se abre la edición de ese proveedor
- **THEN** el campo muestra «12.345.678-5»

#### Scenario: Formato y aviso en vivo con JavaScript
- **WHEN** con JavaScript activo la persona escribe «123456785»
- **THEN** el campo muestra «12.345.678-5» con el cursor tras el mismo dígito y la región `aria-live="polite"` dice «RUT válido.»

#### Scenario: Error solo al salir del campo
- **WHEN** con JavaScript activo la persona escribe «123456789» y luego sale del campo
- **THEN** mientras escribe no aparece ningún error, y al salir el aviso muestra «El dígito verificador del RUT no es correcto.» y el campo queda con `aria-invalid="true"`

#### Scenario: El JavaScript no cambia un RUT sin avisar
- **WHEN** con JavaScript activo la persona escribe una letra distinta de K, una coma o más de 9 dígitos, o pega un texto que no es un RUT
- **THEN** el campo conserva exactamente lo escrito y, al enviar, el servidor muestra el error

#### Scenario: Campo y aviso enlazados
- **WHEN** se abre un formulario con un campo de RUT, con o sin error
- **THEN** el control lleva `aria-describedby` con los ids de la ayuda, del aviso y, si hay error, del error, y los campos que no son de RUT no cambian

#### Scenario: Sin JavaScript
- **WHEN** el navegador no ejecuta JavaScript y se envía «12.345.678-5»
- **THEN** se guarda `12345678-5` igual que con JavaScript

#### Scenario: Acceso por rol sin cambios
- **WHEN** un residente intenta abrir la lista de usuarios, el formulario de proveedor o la página de Unidades
- **THEN** recibe "No tienes permisos" (403)
- **AND** el administrador ve los RUT con puntos en usuarios, proveedores y Unidades, y el comité ve proveedores con puntos pero Unidades sin RUT de residentes

### Requirement: Panel con tarjetas por estado
El sistema SHALL mostrar en el panel de inicio una tarjeta por estado, con nombre, cantidad y una frase, cuyo enlace entero lleva al listado correspondiente: unidades al día, con deuda y morosas, incidentes recibidos y en proceso, y reservas próximas. Las cantidades MUST salir solo del condominio activo, y las de unidades del reporte de cobranza, sin recalcular la morosidad.

#### Scenario: Cantidades del administrador
- **WHEN** el administrador abre el inicio de un condominio con unidades al día, con deuda y morosas, incidentes recibidos y en proceso, y reservas confirmadas desde hoy
- **THEN** cada tarjeta muestra su cantidad correcta y las tres de unidades suman las unidades del período; el comité ve las mismas seis tarjetas

#### Scenario: Aislamiento entre condominios
- **WHEN** otro condominio tiene incidentes, reservas y unidades con deuda
- **THEN** ninguna cantidad del panel los incluye

#### Scenario: Enlace de la tarjeta
- **WHEN** el administrador abre la tarjeta de incidentes en proceso
- **THEN** llega a la lista de incidentes filtrada por `?estado=EN_PROCESO`

#### Scenario: Conserje
- **WHEN** un conserje abre el inicio
- **THEN** ve las tarjetas de incidentes y reservas y ninguna de unidades ni de dinero

#### Scenario: Residente
- **WHEN** un residente abre el inicio
- **THEN** no ve tarjetas por estado y conserva las suyas

#### Scenario: Sin períodos emitidos
- **WHEN** el condominio aún no emite gastos comunes
- **THEN** el administrador no ve tarjetas de unidades y el panel conserva el aviso de que aún no hay indicadores

#### Scenario: Pantallas angostas y anchas
- **WHEN** el panel se abre a 375 px y a 1440 px
- **THEN** no hay desborde horizontal ni tarjetas solapadas, y desde 992 px las tarjetas se muestran de tres en tres (administrador y comité en dos filas, el conserje en una)

### Requirement: Colores por estado accesibles
El sistema SHALL definir un color por estado en variables CSS (`--estado-*`, con su fondo y su texto) que alcancen contraste AA (3:1 el acento, 4,5:1 el texto sobre su fondo), y MUST NOT usar el color como único indicador: toda tarjeta o etiqueta de estado lleva también su nombre en texto. Las tarjetas enlace SHALL tener nombre accesible y foco visible.

#### Scenario: Tarjeta como enlace
- **WHEN** una persona recorre el panel con el teclado
- **THEN** cada tarjeta recibe el foco con un contorno visible y su nombre accesible incluye el estado y la cantidad

### Requirement: Listados con chips de estado y filtros por GET
El sistema SHALL mostrar sobre los listados de incidentes, reporte de recaudación, egresos del período y unidades una fila de chips con la cantidad de cada estado, y filtrar por parámetros GET leídos a mano en la vista. Cada cantidad MUST salir del mismo queryset que el listado, ya filtrado por condominio activo y por rol, antes de aplicar el filtro. Un valor desconocido MUST ignorarse sin error.

#### Scenario: Valor desconocido
- **WHEN** una persona con acceso abre un listado con `?estado=XYZ`
- **THEN** ve el listado completo, sin error, y el chip «Todos» queda activo

### Requirement: Chips accesibles que conservan la URL
El chip activo SHALL llevar `aria-current="true"` y cada cantidad un texto oculto para lectores (por ejemplo «12 incidentes»). «Limpiar filtros» SHALL aparecer solo si hay algún filtro activo, y los chips y la paginación MUST conservar los demás parámetros de la URL.

#### Scenario: Chip y paginación conservan la URL
- **WHEN** hay un filtro y otro parámetro en la URL y la persona elige un chip o cambia de página
- **THEN** el resto de los parámetros se conserva, `page` vuelve a 1 al cambiar de chip y «Limpiar filtros» quita solo los filtros

#### Scenario: Lector de pantalla
- **WHEN** un lector de pantalla recorre los chips
- **THEN** anuncia el nombre y la cantidad («Recibido, 12 incidentes») y el activo se anuncia como actual

#### Scenario: Acceso por rol
- **WHEN** un rol sin acceso al listado (por ejemplo un residente al de unidades) lo abre con filtros
- **THEN** recibe 403 igual que sin filtros

### Requirement: Insignias de estado accesibles
El sistema SHALL mostrar el estado de incidentes, períodos y unidades con insignias `.insignia-*` que usan `--estado-*`, `--estado-*-fondo` y `--estado-*-texto`, con contraste AA, y MUST NOT usar el color como único indicador: la insignia siempre lleva el nombre del estado.

#### Scenario: Contraste de las insignias
- **WHEN** se comprueban los pares texto/fondo de cada insignia
- **THEN** todos alcanzan 4,5:1 y el borde de acento alcanza 3:1 sobre su fondo

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
