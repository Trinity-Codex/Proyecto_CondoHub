# Spec Delta

## ADDED Requirements

### Requirement: Registro de auditoría
El sistema SHALL guardar un registro por cada cambio sobre dinero, roles, alícuotas, datos personales e incidentes,
con el usuario que lo hizo, el condominio, la acción, el objeto afectado, los valores anteriores y los nuevos, y la
fecha y hora. Los registros MUST ser inmutables: ninguna persona puede editarlos ni borrarlos desde el sitio.
Solo el administrador y el comité SHALL ver el registro de su condominio; los demás roles reciben 403.

#### Scenario: Cambio con valores anteriores y nuevos
- **WHEN** el administrador cambia la alícuota de una unidad
- **THEN** el sistema guarda un registro con su usuario, el condominio, la acción, la unidad, la alícuota anterior, la nueva y la fecha y hora

#### Scenario: Evento sin valores anteriores
- **WHEN** el sistema registra la creación de un pago sin valores anteriores
- **THEN** el registro se guarda con los valores anteriores vacíos y el resto de los datos completos

#### Scenario: Intento de editar o borrar un registro
- **WHEN** una persona intenta modificar o borrar un registro de auditoría desde el sitio o el panel de administración
- **THEN** la acción se rechaza y el registro queda sin cambios

#### Scenario: Conserje o residente intenta ver el registro
- **WHEN** un residente o un conserje abre la página de auditoría
- **THEN** ve la página "No tienes permisos" (403)

#### Scenario: Comité revisa la auditoría de su condominio
- **WHEN** un miembro del comité filtra la auditoría por fecha o por usuario
- **THEN** ve solo los registros de su condominio, sin registros de otros condominios
