## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Uso desde el celular
El sistema SHALL adaptar todas las páginas a pantallas desde 360 px, mostrando las tablas como tarjetas en el celular, sin desplazamiento horizontal de la página (el texto oculto para lectores dentro de una tabla desplazable MUST NOT ampliar el ancho), y SHALL poder instalarse como aplicación web (manifest e íconos).

#### Scenario: Tabla en el celular
- **WHEN** un residente abre Mi cuenta en una pantalla de 360 px
- **THEN** ve sus cobros sin desplazamiento horizontal

#### Scenario: Proveedores en el celular
- **WHEN** el administrador abre `/proveedores/` a 375 px
- **THEN** el ancho del documento no supera el de la pantalla
