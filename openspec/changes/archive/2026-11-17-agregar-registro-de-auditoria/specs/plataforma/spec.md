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
- **WHEN** se registra un pago
- **THEN** la auditoría guarda quién lo registró, el condominio, el pago, el monto y el medio, con los valores anteriores vacíos

#### Scenario: Cambio de estado de un incidente
- **WHEN** un administrador o conserje cambia el estado de un incidente de su condominio
- **THEN** la auditoría guarda quién lo cambió y el estado anterior y el nuevo

#### Scenario: Operación revertida
- **WHEN** se revierte la transacción que registra un pago o cambia el estado de un incidente
- **THEN** tampoco queda guardado su registro de auditoría

#### Scenario: Intento de editar o borrar un registro
- **WHEN** una persona intenta modificar o borrar un registro de auditoría desde el sitio o el panel de administración
- **THEN** la acción se rechaza y el registro queda sin cambios

#### Scenario: Conserje o residente intenta ver el registro
- **WHEN** un residente o un conserje abre la página de auditoría
- **THEN** ve la página "No tienes permisos" (403)

#### Scenario: Comité revisa la auditoría de su condominio
- **WHEN** un miembro del comité filtra la auditoría por fecha o por usuario
- **THEN** ve solo los registros de su condominio, sin registros de otros condominios
