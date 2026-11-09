# Spec Delta

## ADDED Requirements

### Requirement: RUT legible en formularios y listados
Los campos de RUT SHALL aceptarlo con o sin puntos, guardarlo normalizado (`12345678-5`) y mostrarse con un ejemplo ficticio válido; los listados SHALL mostrarlo con puntos. Con JavaScript SHALL formatearse en vivo y avisar «RUT válido.» en `aria-live="polite"`, y MUST mostrar el error solo al salir del campo, sin cambiar dígitos sin avisar. Todo SHALL funcionar sin JavaScript, sin cambiar validación, permisos ni lo guardado.

#### Scenario: Mostrar con puntos
- **WHEN** un listado muestra los RUT guardados `12345678-5`, `1234567-4` y `96511790-K`
- **THEN** se ven «12.345.678-5», «1.234.567-4» y «96.511.790-K», y un texto que no es un RUT se ve igual que está guardado

#### Scenario: Guardar normalizado
- **WHEN** el administrador registra un proveedor o a un usuario escribiendo «12.345.678-5» o «12345678-5»
- **THEN** se guarda `12345678-5` en ambos casos

#### Scenario: RUT con K y de 7 dígitos
- **WHEN** se escribe «96.511.790-k» o «1.234.567-4»
- **THEN** ambos se aceptan y se guardan `96511790-K` y `1234567-4`

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
