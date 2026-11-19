## MODIFIED Requirements

### Requirement: Fondo de reserva
El sistema SHALL calcular el saldo del condominio sumando sus movimientos en pesos enteros: saldo inicial, ingresos, egresos y ajustes. Solo el administrador registra movimientos manuales; el comité consulta. Cada egreso MUST guardar descripción, fecha, monto positivo, proveedor opcional del mismo condominio y acuerdo autorizante. El sistema MUST auditar cada movimiento manual y aislar los datos por condominio. El sistema SHALL mostrar su evolución mensual por edificio, unidad y residente.

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
- **WHEN** un conserje o un residente intenta consultar el libro de movimientos, la evolución mensual o el desglose por edificio, o acceder por GET o POST a las operaciones manuales
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

#### Scenario: Evolución mensual cuadra con el corte mensual
- **WHEN** el administrador o el comité abre la evolución del fondo con saldo inicial, aportes emitidos, egresos y ajustes en varios meses
- **THEN** cada mes muestra saldo de apertura, aportes, egresos, ajustes y saldo de cierre, donde apertura más movimientos del mes es igual al cierre, el cierre es igual al saldo de corte de ese mes y el gráfico muestra los mismos cierres que la tabla

#### Scenario: Mes sin período emitido
- **WHEN** un mes entre la apertura del fondo y el mes actual no tiene período emitido
- **THEN** la fila y su barra se marcan «sin período emitido», sin aporte inventado, y su cierre solo refleja los movimientos registrados de ese mes

#### Scenario: Evolución sin cobertura
- **WHEN** se abre la evolución de un condominio con períodos emitidos y sin saldo inicial configurado
- **THEN** se informa que falta configurar el saldo inicial y no se muestra una serie ni un saldo cero inventados

#### Scenario: Aportes y saldo por edificio
- **WHEN** el administrador o el comité consulta el desglose por edificio
- **THEN** ve por mes la suma de los aportes de las unidades de cada edificio, y un saldo por edificio igual a sus aportes más su parte, según la suma de alícuotas de sus unidades, de los movimientos del condominio (saldo inicial, egresos y ajustes), repartida sin perder pesos, de modo que los saldos de los edificios suman el saldo total

#### Scenario: Aporte acumulado por unidad y por residente
- **WHEN** el administrador o el comité consulta los aportes por unidad
- **THEN** ve el aporte acumulado de cada unidad de su condominio en los períodos emitidos y, para cada residente vigente, solo los aportes de los meses que se superponen con su período de residencia en esa unidad, sin listar residencias dadas de baja

#### Scenario: Ítems de cobro fuera del fondo
- **WHEN** un período emitido incluye ítems de cobro
- **THEN** los aportes de la evolución, del edificio, de la unidad y del residente cuentan solo el aporte al fondo de reserva de cada cobro, sin los ítems

#### Scenario: Residente ve su propio aporte
- **WHEN** un residente abre su vista del fondo
- **THEN** ve el saldo total del fondo y el aporte acumulado y mensual de sus unidades solo en los meses de su residencia, sin datos de otras unidades ni del desglose por edificio

#### Scenario: Residente pide el desglose de otra unidad
- **WHEN** un residente pide por URL el desglose de una unidad de su condominio donde no reside
- **THEN** recibe 403 sin importes de esa unidad

#### Scenario: Unidad de otro condominio
- **WHEN** un administrador, miembro del comité o residente pide por URL el desglose de una unidad de otro condominio
- **THEN** recibe 404 y la evolución, el desglose por edificio y los aportes por unidad tampoco incluyen datos ajenos

#### Scenario: Conserje sin acceso a aportes
- **WHEN** un conserje sin otro rol pide la vista del residente o el desglose de una unidad
- **THEN** recibe 403
