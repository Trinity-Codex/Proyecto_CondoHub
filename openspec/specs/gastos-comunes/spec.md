# gastos-comunes Specification

## Purpose
Registrar los egresos de cada mes y emitir los gastos comunes de cada unidad con un prorrateo
configurable y el fondo de reserva (RF02). Código: `apps/gastos` (`prorrateo.py`, `servicios.py`).

## Requirements

### Requirement: Período mensual de gastos
El sistema SHALL manejar un período por mes y condominio, en estado ABIERTO o EMITIDO, con su criterio de prorrateo y su porcentaje de fondo de reserva, que MUST ser de al menos 5 % (Ley 21.442).

#### Scenario: Período repetido
- **WHEN** el administrador abre un período para un mes que ya existe en el condominio
- **THEN** el formulario lo rechaza

#### Scenario: Fondo de reserva bajo el mínimo
- **WHEN** el porcentaje del fondo de reserva es menor que 5
- **THEN** el formulario lo rechaza

### Requirement: Egresos del período
El sistema SHALL registrar los egresos de un período abierto con categoría, descripción, monto, fecha y proveedor opcional; solo el administrador los crea, edita o elimina.

#### Scenario: Comité consulta los egresos
- **WHEN** un miembro del comité abre un período
- **THEN** ve sus egresos y no tiene opciones para modificarlos

### Requirement: Prorrateo intercambiable
El sistema SHALL repartir el total del período entre las unidades según el criterio elegido, por alícuota o en partes iguales (patrón Strategy), y MUST redondear con el método del resto mayor para que la suma de los cobros sea exactamente el total.

#### Scenario: Suma exacta
- **WHEN** se emite un período cuyo total no se divide en partes enteras
- **THEN** la suma de los cobros de las unidades es igual al total, sin pesos perdidos ni sobrantes

### Requirement: Emisión del período
El sistema SHALL emitir un período creando un cobro por unidad con su parte de los gastos y su aporte al fondo de reserva, notificar a los residentes y MUST impedir modificar un período emitido o emitirlo dos veces.

#### Scenario: Emisión bloqueada por alícuotas
- **WHEN** el criterio es por alícuota y las alícuotas de las unidades no suman 1
- **THEN** la emisión se rechaza con un mensaje que indica la suma actual

#### Scenario: Emisión sin egresos
- **WHEN** el administrador intenta emitir un período sin egresos
- **THEN** la emisión se rechaza

#### Scenario: Doble clic al emitir
- **WHEN** llegan dos solicitudes de emisión simultáneas del mismo período
- **THEN** se crea un solo juego de cobros
