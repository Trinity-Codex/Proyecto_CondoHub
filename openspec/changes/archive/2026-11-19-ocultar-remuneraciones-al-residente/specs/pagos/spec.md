# Spec Delta

## MODIFIED Requirements

### Requirement: Estado de cuenta del residente
El sistema SHALL mostrar en "Mi cuenta" los cobros de las unidades donde la persona es residente activa cuyo período se superpone con su residencia, con lo pagado y el saldo de cada uno, y el detalle de cada cobro. En ese detalle los egresos del período SHALL mostrarse agrupados por categoría con su subtotal, con las remuneraciones como una sola línea «Remuneraciones del personal», sin descripción libre, proveedor ni fecha de boleta; la suma de los subtotales MUST ser el total de egresos del período. Un período se superpone si la residencia cubre al menos un día de ese mes. La deuda mostrada en el panel de inicio MUST seguir la misma regla.

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


#### Scenario: Egresos agrupados sin remuneraciones individuales
- **WHEN** un residente abre el detalle de su cobro y el período tiene los sueldos «Sueldo conserje (jornada completa)» y «Sueldo personal de aseo»
- **THEN** ve una sola línea «Remuneraciones del personal» con la suma de ambos, no ve ninguna descripción libre de los egresos y la suma de los subtotales es igual al total de egresos del período

#### Scenario: Detalle completo solo para la administración
- **WHEN** un residente pide por URL directa el detalle de un período en gastos
- **THEN** el sistema responde 403, y el administrador y el comité reciben 200 con el detalle línea a línea

#### Scenario: Categoría fuera de las opciones del modelo
- **WHEN** un residente abre el detalle de un cobro cuyo período tiene un egreso con una categoría que no está entre las opciones del modelo
- **THEN** el sistema responde 200 y muestra esa categoría con su valor crudo y su subtotal, sin la descripción del egreso

#### Scenario: Período con un solo egreso de remuneraciones
- **WHEN** un residente abre el detalle de un cobro cuyo período solo tiene un egreso de remuneraciones
- **THEN** ve la línea «Remuneraciones del personal» con ese subtotal (riesgo aceptado, ver design.md) y no ve la descripción libre del egreso
