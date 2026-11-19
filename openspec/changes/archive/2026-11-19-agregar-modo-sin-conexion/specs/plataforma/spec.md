## MODIFIED Requirements

### Requirement: Uso desde el celular
El sistema SHALL adaptar todas las páginas a pantallas desde 360 px, mostrando las tablas como tarjetas en el celular, sin desplazamiento horizontal de la página (el texto oculto para lectores dentro de una tabla desplazable MUST NOT ampliar el ancho), y SHALL poder instalarse como aplicación web (manifest e íconos). Tras la primera instalación del service worker, la navegación sin red MUST mostrar una página pública de reintento.

#### Scenario: Tabla en el celular
- **WHEN** un residente abre Mi cuenta en una pantalla de 360 px
- **THEN** ve sus cobros sin desplazamiento horizontal

#### Scenario: Proveedores en el celular
- **WHEN** el administrador abre `/proveedores/` a 375 px
- **THEN** el ancho del documento no supera el de la pantalla

#### Scenario: Pérdida y recuperación de conexión
- **WHEN** se pierde internet después de activar el service worker
- **THEN** al navegar se muestra «Sin conexión» y, al recuperar la red, reintentar abre la página solicitada

#### Scenario: Datos privados
- **WHEN** se consulta una página autenticada o se envía un formulario
- **THEN** el service worker solo conserva en caché los recursos públicos de la lista de estáticos
