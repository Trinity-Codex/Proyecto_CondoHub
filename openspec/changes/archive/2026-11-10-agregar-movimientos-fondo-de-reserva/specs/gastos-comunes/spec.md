# Spec Delta

## ADDED Requirements

### Requirement: Fondo de reserva
El sistema SHALL calcular el saldo del condominio sumando sus movimientos en pesos enteros: saldo inicial, ingresos, egresos y ajustes. Solo el administrador registra movimientos manuales; el comité consulta. Cada egreso MUST guardar descripción, fecha, monto positivo, proveedor opcional del mismo condominio y acuerdo autorizante. El sistema MUST auditar cada movimiento manual y aislar los datos por condominio.

#### Scenario: Administrador configura el saldo inicial
- **WHEN** el administrador registra el saldo inicial con monto no negativo, fecha y descripción de su origen
- **THEN** se crea un único movimiento inicial para su condominio y su evento de auditoría, sin guardar un saldo separado

#### Scenario: Saldo inicial repetido
- **WHEN** el administrador intenta registrar un segundo saldo inicial para el mismo condominio
- **THEN** se rechaza sin crear movimiento ni evento de auditoría

#### Scenario: Administrador registra un egreso autorizado
- **WHEN** el administrador registra un egreso válido con la referencia del acuerdo autorizante
- **THEN** el movimiento disminuye el saldo por ese monto y queda auditado con su autor

#### Scenario: Egreso inválido
- **WHEN** el administrador registra un egreso sin descripción, fecha o acuerdo, con monto no positivo, o con un proveedor ajeno
- **THEN** el formulario indica el error y no crea movimiento ni evento de auditoría

#### Scenario: Comité solo consulta
- **WHEN** el comité abre el fondo e intenta acceder por GET o POST a un formulario de saldo inicial, egreso o ajuste
- **THEN** puede consultar saldo y movimientos, y las operaciones manuales responden 403 sin cambios

#### Scenario: Conserje y residente sin acceso al fondo
- **WHEN** un conserje o un residente intenta consultar el fondo o acceder por GET o POST a sus operaciones manuales
- **THEN** recibe 403 sin acceder a datos ni crear movimientos

#### Scenario: Movimiento de otro condominio
- **WHEN** un administrador o miembro del comité abre por URL un movimiento de otro condominio
- **THEN** recibe 404 y el listado tampoco muestra movimientos ajenos

#### Scenario: Saldo igual a movimientos y aportes cobrados
- **WHEN** se consulta el fondo con saldo inicial, ingresos de emisiones nuevas, egresos y ajustes registrados
- **THEN** el saldo es la suma algebraica de esos movimientos y cada ingreso coincide exactamente con los aportes incluidos en los cobros de su período

#### Scenario: Corte mensual inclusivo para C5
- **WHEN** se consulta el saldo hasta un período del mismo condominio
- **THEN** incluye el aporte emitido de ese período y todos los movimientos de fecha contable hasta el último día de su mes, excluyendo los posteriores aunque el aporte se haya emitido durante el mes siguiente

#### Scenario: Movimientos mensuales para C5
- **WHEN** se consultan los movimientos de un período del mismo condominio
- **THEN** se devuelven únicamente los de su mes contable, ordenados por fecha e identificador, con monto firmado, tipo, descripción, proveedor opcional, acuerdo y período de origen

#### Scenario: Período ajeno en C5
- **WHEN** una consulta de saldo o movimientos recibe un período de otro condominio
- **THEN** rechaza la consulta sin devolver importes ni movimientos ajenos

#### Scenario: Fondo sin movimientos
- **WHEN** se consulta un fondo que no tiene movimientos ni períodos emitidos anteriores a la activación
- **THEN** el saldo es el entero cero y la lista de movimientos está vacía

#### Scenario: Históricos anteriores a la activación
- **WHEN** se aplica la migración sobre un condominio con períodos ya emitidos
- **THEN** no se generan ingresos retroactivos; el administrador debe registrar el saldo inicial documentado y las consultas históricas sin cobertura se rechazan expresamente, sin inventar un saldo cero

#### Scenario: Ajuste trazable
- **WHEN** el administrador registra una corrección no nula con fecha, descripción y referencia justificativa
- **THEN** se agrega un movimiento compensatorio auditado, conservando los movimientos anteriores sin editarlos ni eliminarlos

#### Scenario: Fallo de auditoría de un movimiento manual
- **WHEN** falla el registro de auditoría al guardar un saldo inicial, egreso o ajuste
- **THEN** no se guarda el movimiento y el saldo permanece igual

#### Scenario: Movimiento manual anterior a la apertura
- **WHEN** el administrador intenta registrar un egreso o ajuste con fecha anterior al movimiento inicial del legado
- **THEN** se rechaza sin cambios y se informa la fecha desde la que hay cobertura

#### Scenario: Saldo contable negativo
- **WHEN** un egreso autorizado o ajuste documentado deja el saldo bajo cero
- **THEN** se conserva el movimiento auditado y el saldo negativo se muestra explícitamente como contable

## MODIFIED Requirements

### Requirement: Emisión del período
El sistema SHALL emitir un período creando un cobro por unidad con su parte de los gastos y su aporte al fondo de reserva, notificar a los residentes y MUST impedir modificar un período emitido o emitirlo dos veces. En la misma operación MUST crear un ingreso único al fondo igual a la suma de los aportes cobrados y auditar la emisión; si falla, no persiste ninguno de esos cambios.

#### Scenario: Emisión bloqueada por alícuotas
- **WHEN** el criterio es por alícuota y las alícuotas de las unidades no suman 1
- **THEN** la emisión se rechaza con un mensaje que indica la suma actual

#### Scenario: Emisión sin egresos
- **WHEN** el administrador intenta emitir un período sin egresos
- **THEN** la emisión se rechaza

#### Scenario: Doble clic al emitir
- **WHEN** llegan dos solicitudes de emisión simultáneas del mismo período
- **THEN** se crea un solo juego de cobros, un solo ingreso al fondo y un solo evento de emisión

#### Scenario: Administrador emite e ingresa el aporte exacto
- **WHEN** el administrador emite un período válido, aun si el reparto requiere redondeo
- **THEN** el ingreso es exactamente la suma de los aportes de los cobros guardados, queda asociado al período y se registra la emisión con el administrador como autor

#### Scenario: Comité consulta pero no emite
- **WHEN** el comité consulta el período e intenta abrir o confirmar su emisión
- **THEN** conserva el acceso de consulta y recibe 403 en GET y POST de emisión, sin ingreso nuevo

#### Scenario: Conserje y residente sin acceso a la emisión
- **WHEN** un conserje o un residente intenta abrir el período o ejecutar GET o POST de emisión
- **THEN** recibe 403 sin crear cobros ni ingresos

#### Scenario: Período de otro condominio al emitir
- **WHEN** el administrador intenta abrir o confirmar la emisión de un período ajeno
- **THEN** recibe 404 sin crear cobros, movimientos ni eventos

#### Scenario: Emisión atómica
- **WHEN** falla la creación del ingreso, la auditoría o la notificación persistida durante la emisión
- **THEN** el período sigue abierto y no quedan cobros, ingreso, notificaciones ni auditoría parciales

#### Scenario: Aporte redondeado a cero
- **WHEN** se emite un período válido cuyo aporte total se redondea a cero pesos
- **THEN** se conserva el ingreso único de cero pesos asociado a esa emisión y el saldo no cambia

#### Scenario: Emisión anterior a la apertura
- **WHEN** el administrador intenta emitir un período cuya fecha contable precede a la apertura del legado
- **THEN** se rechaza sin cerrar el período ni crear cobros, ingresos, notificaciones o auditoría
