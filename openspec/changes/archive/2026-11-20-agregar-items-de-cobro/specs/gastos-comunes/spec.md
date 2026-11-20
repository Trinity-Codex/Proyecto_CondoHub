## ADDED Requirements

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

## MODIFIED Requirements

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
