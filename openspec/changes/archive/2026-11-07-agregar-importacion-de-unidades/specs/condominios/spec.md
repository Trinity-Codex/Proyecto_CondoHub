# Spec Delta

## ADDED Requirements

### Requirement: Importación desde planilla
El sistema SHALL permitir que el administrador importe al condominio activo edificios, unidades y residentes desde un archivo CSV, con una vista previa de los errores por fila antes de confirmar. La importación MUST ser todo o nada y reimportar el mismo archivo MUST NOT duplicar datos.

#### Scenario: Vista previa sin errores
- **WHEN** el administrador sube un CSV válido
- **THEN** el sistema muestra cuántos edificios, unidades, cuentas y residentes se crearán o actualizarán, sin guardar nada todavía

#### Scenario: Errores por fila
- **WHEN** el archivo tiene una fila con RUT inválido, un correo repetido con otros datos, una unidad repetida o una alícuota o fecha inválida
- **THEN** la vista previa muestra el número de fila y el error, y no permite confirmar

#### Scenario: Alícuotas que no suman 1
- **WHEN** las alícuotas del condominio, con las del archivo, no suman 1
- **THEN** la vista previa lo indica como error y no permite confirmar

#### Scenario: Todo o nada
- **WHEN** falla el guardado de una fila al confirmar
- **THEN** no queda guardada ninguna fila del archivo

#### Scenario: Reimportar el mismo archivo
- **WHEN** el administrador importa dos veces el mismo archivo
- **THEN** el condominio queda con los mismos edificios, unidades, cuentas y residentes que después de la primera vez

#### Scenario: Cuentas nuevas e invitaciones
- **WHEN** el archivo trae el correo de una persona sin cuenta y el administrador confirma con «Enviar invitaciones»
- **THEN** se crea la cuenta, queda como residente con su fecha de inicio y recibe el correo para definir su contraseña; sin esa opción, no se envía ningún correo

#### Scenario: Plantilla de ejemplo
- **WHEN** el administrador descarga la plantilla
- **THEN** recibe un CSV con los encabezados y filas de ejemplo que la misma importación acepta

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente intenta importar o descargar la plantilla
- **THEN** el sistema responde 403
