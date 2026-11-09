# plataforma Specification

## Purpose
Requisitos transversales de la aplicación: acceso desde el celular, instalación como PWA, respuestas de
error y protecciones generales (RNF02, RNF03, RNF06, RNF13). Código: `config/`, `templates/`, `static/`, `apps/core`.

## Requirements

### Requirement: Uso desde el celular
El sistema SHALL adaptar todas las páginas a pantallas desde 360 px, mostrando las tablas como tarjetas en el celular, y SHALL poder instalarse como aplicación web (manifest e íconos).

#### Scenario: Tabla en el celular
- **WHEN** un residente abre Mi cuenta en una pantalla de 360 px
- **THEN** ve sus cobros sin desplazamiento horizontal

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
