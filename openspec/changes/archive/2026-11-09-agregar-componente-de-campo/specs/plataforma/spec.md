# Spec Delta

## ADDED Requirements

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
