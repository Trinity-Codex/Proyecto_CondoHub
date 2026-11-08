# Spec Delta

## MODIFIED Requirements

### Requirement: Estado de cuenta del residente
El sistema SHALL mostrar en "Mi cuenta" los cobros de las unidades donde la persona es residente activa cuyo período se superpone con su residencia, con lo pagado y el saldo de cada uno, y el detalle de cada cobro. Un período se superpone si la residencia cubre al menos un día de ese mes. La deuda mostrada en el panel de inicio MUST seguir la misma regla.

#### Scenario: Residente al día
- **WHEN** un residente cuyos cobros están todos pagados abre Mi cuenta
- **THEN** ve saldo cero

#### Scenario: Cobro de otra unidad
- **WHEN** un residente abre por URL directa el cobro de una unidad que no es suya
- **THEN** el sistema responde 404

#### Scenario: Cobros anteriores a su llegada
- **WHEN** un residente cuya residencia comienza en marzo abre Mi cuenta y su unidad tiene una deuda de febrero
- **THEN** no ve el cobro de febrero y esa deuda no se suma a su saldo ni a la deuda de su panel de inicio

#### Scenario: Llegada a mitad de mes
- **WHEN** un residente cuya residencia comienza el 20 de marzo abre Mi cuenta
- **THEN** ve el cobro completo de marzo

#### Scenario: Cobro fuera de su período por URL directa
- **WHEN** un residente abre por URL directa un cobro de su unidad de un período anterior a su residencia
- **THEN** el sistema responde 404

#### Scenario: Residente dado de baja
- **WHEN** una persona dada de baja de una unidad, que sigue siendo residente activa de otra unidad, abre Mi cuenta
- **THEN** ve solo los cobros de la unidad donde sigue activa

### Requirement: Cobranza por unidad
El sistema SHALL mostrar al administrador y al comité la deuda de cada unidad del condominio activo y la cuenta completa de cada unidad, sin limitarla por las fechas de residencia.

#### Scenario: Comité consulta la cobranza
- **WHEN** un miembro del comité abre la cobranza
- **THEN** ve la deuda por unidad y no puede registrar pagos

#### Scenario: Deuda anterior al residente actual
- **WHEN** el administrador abre la cuenta de una unidad con una deuda anterior a la llegada de su residente actual
- **THEN** ve la deuda completa de la unidad
