# gastos-comunes Specification

## Purpose
Registrar los egresos de cada mes y emitir los gastos comunes de cada unidad con un prorrateo
configurable y el fondo de reserva (RF02). Código: `apps/gastos` (`prorrateo.py`, `servicios.py`).

## Requirements

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

#### Scenario: Vencimiento del aviso
- **WHEN** se descarga el aviso de una unidad de un período emitido
- **THEN** muestra el vencimiento del período y la referencia del reglamento si el reparto es en partes iguales

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
El sistema SHALL emitir un período creando un cobro por unidad con su parte de los gastos, su aporte al fondo de reserva y la suma de los ítems de cobro que la alcanzan, cada ítem como una línea separada del cobro, notificar a los residentes y MUST impedir modificar un período emitido o emitirlo dos veces. En la misma operación MUST crear un ingreso único al fondo igual a la suma de los aportes cobrados y auditar la emisión; si falla, no persiste ninguno de esos cambios.

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

#### Scenario: Emisión con ítems de cobro
- **WHEN** el administrador emite un período con un ítem general y una multa a una unidad
- **THEN** el cobro de cada unidad incluye una línea por ítem que la alcanza, su total suma gastos, fondo e ítems, y el fondo de reserva se calcula solo sobre los egresos

#### Scenario: Ítem sin unidades que lo paguen
- **WHEN** un ítem a prorratear alcanza solo unidades cuya alícuota suma cero
- **THEN** la emisión se rechaza con un mensaje que nombra el ítem

#### Scenario: Ítem guardado mientras se emite
- **WHEN** el administrador guarda o elimina un ítem al mismo tiempo que se emite su período
- **THEN** la operación que llega después de la emisión se rechaza y los cobros emitidos coinciden con los ítems guardados

### Requirement: Filtro de egresos por categoría
El sistema SHALL filtrar los egresos de un período con `?categoria=<categoría>` y mostrar chips con la cantidad de egresos de cada categoría del período, conservando su orden actual (fecha y luego id, del más antiguo al más reciente). Administrador y comité ven el listado; el filtro no da acceso a períodos de otro condominio.

#### Scenario: Egresos de una categoría
- **WHEN** el comité abre el período con `?categoria=` de una categoría que tiene egresos
- **THEN** ve solo esos egresos, el total del período sigue siendo el de todos y los chips cuentan todas las categorías

#### Scenario: Período de otro condominio
- **WHEN** alguien abre por URL el período de otro condominio con un filtro
- **THEN** el sistema responde 404

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

### Requirement: Aviso de cobro
El sistema SHALL entregar al residente y al administrador un aviso PDF por unidad y período emitido, con desglose, pagos vigentes, saldo anterior visible, total a pagar, caja registrada y egresos agrupados sin descripciones personales. Los importes MUST expresarse en pesos chilenos.

#### Scenario: Consulta de la deuda
- **WHEN** hay pagos parciales y saldos de períodos anteriores visibles
- **THEN** el aviso suma el saldo del cobro y la deuda anterior de esa unidad hasta el período elegido

#### Scenario: Acceso del residente
- **WHEN** el residente solicita un aviso ajeno o anterior a su residencia
- **THEN** el sistema responde 404

#### Scenario: Caja sin saldo inicial conciliado
- **WHEN** la caja solo contiene movimientos registrados
- **THEN** el PDF identifica su alcance y muestra «Documento de demostración»

### Requirement: Saldo del fondo en el aviso de cobro
El aviso SHALL mostrar el saldo contable del fondo de reserva del condominio al cierre del mes según su libro de movimientos.

#### Scenario: Período sin historia contable suficiente
- **WHEN** el período no tiene cobertura del libro del fondo
- **THEN** el aviso y la rendición indican que el histórico no está disponible

#### Scenario: Saldo disponible
- **WHEN** un período dispone de cobertura contable
- **THEN** el saldo de fondo del aviso coincide con el de la rendición

### Requirement: Ítems de cobro
El sistema SHALL permitir solo al administrador registrar, editar y eliminar ítems de cobro de un período abierto (nombre, monto en pesos, modo y alcance: todas las unidades o algunas del condominio) y MUST auditar cada cambio. El modo «monto por unidad» cobra ese monto a cada unidad alcanzada; «total a prorratear» lo reparte por alícuota entre ellas con el método del resto mayor.

#### Scenario: Administrador registra una multa a una unidad
- **WHEN** el administrador crea en un período abierto un ítem de $25.000 «monto por unidad» dirigido a una unidad
- **THEN** el ítem queda en el período, se registra la creación en la auditoría y, al emitir, solo esa unidad paga $25.000 adicionales

#### Scenario: Cuota extraordinaria prorrateada
- **WHEN** el administrador crea un ítem «total a prorratear» para todas las unidades cuyo total no se divide en partes enteras
- **THEN** al emitir, cada unidad paga su parte según su alícuota y la suma de las partes es exactamente el total del ítem

#### Scenario: Ítem dirigido sin unidades
- **WHEN** el administrador elige el alcance «solo algunas unidades» sin elegir ninguna o con una unidad de otro condominio
- **THEN** el formulario se rechaza y no se guarda el ítem

#### Scenario: Período emitido
- **WHEN** el administrador intenta crear, editar o eliminar un ítem de un período emitido
- **THEN** se rechaza con un aviso y el ítem y los cobros no cambian

#### Scenario: Comité, conserje y residente sin acceso al mantenedor
- **WHEN** un miembro del comité, un conserje o un residente abre o envía el formulario de crear, editar o eliminar un ítem
- **THEN** recibe 403 y no se guarda nada; el comité sigue viendo los ítems en el detalle del período

#### Scenario: Ítem de otro condominio
- **WHEN** el administrador intenta editar o eliminar un ítem de un período de otro condominio
- **THEN** recibe 404 sin cambios ni auditoría

#### Scenario: Residente ve solo sus ítems
- **WHEN** un residente consulta sus cobros emitidos
- **THEN** solo obtiene las líneas de ítems de su unidad en los meses de su residencia; el total adeudado incluye esos ítems
