# Spec Delta

## MODIFIED Requirements

### Requirement: Período mensual de gastos
El sistema SHALL manejar un período por mes y condominio, en estado ABIERTO o EMITIDO, con su criterio de prorrateo, su porcentaje de fondo de reserva, que MUST ser de al menos 5 % (Ley 21.442), y su fecha de vencimiento, que por defecto es el día 10 del mes siguiente. Si el criterio es partes iguales, el período MUST indicar el artículo del reglamento de copropiedad que lo autoriza. Solo el administrador abre o edita un período.

#### Scenario: Período repetido
- **WHEN** el administrador abre un período para un mes que ya existe en el condominio
- **THEN** el formulario lo rechaza

#### Scenario: Fondo de reserva bajo el mínimo
- **WHEN** el porcentaje del fondo de reserva es menor que 5
- **THEN** el formulario lo rechaza

#### Scenario: Vencimiento por defecto
- **WHEN** el administrador abre el período de noviembre de 2026 sin cambiar la fecha de vencimiento propuesta
- **THEN** el período queda con vencimiento el 10 de diciembre de 2026

#### Scenario: Vencimiento dentro del mismo mes
- **WHEN** el administrador indica una fecha de vencimiento anterior al primer día del mes siguiente al período
- **THEN** el formulario la rechaza con un mensaje que indica desde qué fecha puede vencer

#### Scenario: Partes iguales sin referencia del reglamento
- **WHEN** el administrador elige el criterio partes iguales y deja vacía la referencia del reglamento
- **THEN** el formulario lo rechaza y pide el artículo del reglamento que autoriza ese criterio

#### Scenario: Partes iguales con referencia del reglamento
- **WHEN** el administrador elige partes iguales e indica "Art. 12 del reglamento de copropiedad"
- **THEN** el período se guarda y su detalle muestra el criterio y esa referencia

#### Scenario: Períodos anteriores al cambio
- **WHEN** se actualiza la base de datos de un condominio que ya tenía períodos
- **THEN** cada período existente queda con vencimiento el día 10 del mes siguiente a su mes

#### Scenario: Comité consulta el vencimiento
- **WHEN** un miembro del comité abre el detalle de un período
- **THEN** ve la fecha de vencimiento y la referencia del reglamento, y recibe 403 si intenta abrir o editar el período

#### Scenario: Residente o conserje sin acceso al período
- **WHEN** un residente o un conserje intenta abrir el detalle, el formulario de creación o el de edición de un período
- **THEN** recibe 403

#### Scenario: Período de otro condominio
- **WHEN** el administrador intenta editar un período que pertenece a otro condominio
- **THEN** recibe 404
