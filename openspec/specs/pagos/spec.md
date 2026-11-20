# pagos Specification

## Purpose
Mostrar a cada residente lo que debe y registrar los pagos de cada cobro, totales o parciales
(RF03, RF04). Código: `apps/pagos` (`consultas.py`, `models.py`).

## Requirements

### Requirement: Estado de cuenta del residente
Mi cuenta SHALL mostrar los cobros, pagos y saldos de las unidades donde la residencia activa cubra algún día del mes cobrado, y el panel MUST aplicar ese filtro a la deuda. El detalle SHALL agrupar los egresos por categoría con subtotales que sumen el total del período, con las remuneraciones en una sola línea «Remuneraciones del personal» y sin descripciones libres, proveedores ni fechas de boleta. Cada ítem de cobro SHALL figurar como línea con nombre y monto.

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

#### Scenario: Ítems de cobro desglosados en el detalle
- **WHEN** un residente abre el detalle de un cobro que tiene una cuota extraordinaria y una multa
- **THEN** ve una línea por cada ítem con su nombre y monto, y la parte de los gastos, el fondo de reserva y esas líneas suman el total a pagar

#### Scenario: Ítems de cobro en el estado de cuenta, el aviso y la descarga
- **WHEN** un residente abre Mi estado de cuenta, descarga el aviso de cobro en PDF o descarga sus datos, y su cobro tiene ítems
- **THEN** el estado de cuenta muestra en pantallas medianas y grandes el monto de ítems de cada cobro (en el celular el desglose queda en el detalle), y el aviso y la descarga muestran cada línea con su nombre y monto

#### Scenario: Multa dirigida a otra unidad
- **WHEN** el administrador cobra una multa solo a otra unidad del condominio y un residente abre el detalle, el aviso o la descarga de su propio cobro de ese período
- **THEN** no ve la línea de la multa ajena, y el cobro de la otra unidad por URL directa responde 404, igual que un cobro de otro condominio

### Requirement: Cobranza por unidad
El sistema SHALL mostrar al administrador y al comité la deuda de cada unidad del condominio activo y la cuenta completa de cada unidad, sin limitarla por las fechas de residencia.

#### Scenario: Comité consulta la cobranza
- **WHEN** un miembro del comité abre la cobranza
- **THEN** ve la deuda por unidad y no puede registrar pagos

#### Scenario: Deuda anterior al residente actual
- **WHEN** el administrador abre la cuenta de una unidad con una deuda anterior a la llegada de su residente actual
- **THEN** ve la deuda completa de la unidad

### Requirement: Registro de pagos
El sistema SHALL permitir que el administrador registre pagos de un cobro con fecha, monto, medio (transferencia, efectivo, cheque o Webpay como etiqueta) y observación; MUST impedir pagos que superen el saldo, pagos a un cobro ya pagado y fechas futuras; SHALL marcar el cobro como PAGADO cuando los pagos cubren el total; SHALL calcular el saldo solo con los pagos no anulados; y SHALL avisar del pago solo a los residentes activos que ven ese cobro.

#### Scenario: Abono parcial
- **WHEN** el administrador registra un pago menor que el saldo
- **THEN** el cobro sigue pendiente con el saldo restante y el residente recibe un aviso

#### Scenario: Pago en exceso
- **WHEN** el administrador registra un pago mayor que el saldo
- **THEN** el pago se rechaza indicando el saldo pendiente

#### Scenario: Pagos simultáneos
- **WHEN** llegan dos pagos simultáneos que juntos superan el saldo
- **THEN** solo se acepta el que cabe en el saldo

#### Scenario: Pago anulado no cuenta para el saldo
- **WHEN** el administrador registra un pago de un cobro que tiene otro pago anulado
- **THEN** el saldo se calcula sin el pago anulado

#### Scenario: Aviso solo a quien ve el cobro
- **WHEN** el administrador registra un pago de un cobro de febrero en una unidad donde un residente llegó en marzo y otro estaba desde febrero
- **THEN** solo el residente de febrero recibe el aviso, y el residente de marzo no recibe aviso ni enlace a ese cobro

#### Scenario: Residente dado de baja no recibe aviso
- **WHEN** el administrador registra un pago en una unidad donde una persona ya fue dado de baja
- **THEN** esa persona no recibe el aviso

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité o un residente intenta registrar un pago
- **THEN** el sistema responde 403 y no se crea ningún pago

### Requirement: Anulación de pagos
El sistema SHALL permitir que el administrador anule un pago registrado por error, indicando un motivo obligatorio. El pago MUST NOT borrarse: queda marcado como anulado. El cobro SHALL recalcular su estado al anular el pago. El sistema SHALL avisar al residente de la anulación y registrar el evento en la auditoría.

#### Scenario: Anulación que vuelve a dejar el cobro pendiente
- **WHEN** el administrador anula el único pago que cubría el total de un cobro
- **THEN** el cobro vuelve a PENDIENTE con el saldo completo, el pago queda marcado como anulado y el residente recibe un aviso

#### Scenario: Anulación sin motivo
- **WHEN** el administrador intenta anular un pago sin indicar el motivo
- **THEN** la anulación se rechaza y el pago sigue vigente

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité o un residente intenta anular un pago
- **THEN** el sistema responde 403 y el pago no cambia

#### Scenario: Pago de otro condominio
- **WHEN** el administrador intenta anular un pago de un cobro de otro condominio
- **THEN** el sistema responde 404 y el pago no cambia

### Requirement: Comprobante de pago
El sistema SHALL permitir descargar el comprobante PDF de un pago con número, fecha, monto, medio, cobro abonado y saldo pendiente al descargarlo. El administrador MUST acceder solo a pagos de su condominio activo y el residente solo a pagos de sus cobros visibles.

#### Scenario: Abono vigente
- **WHEN** el residente descarga el comprobante desde un cobro visible
- **THEN** el documento muestra el abono seleccionado y el saldo actual del cobro

#### Scenario: Pago anulado
- **WHEN** el administrador o el residente descarga el comprobante de un pago anulado
- **THEN** el PDF muestra Anulado y su importe no reduce el saldo

#### Scenario: Cobro ajeno
- **WHEN** el residente solicita un pago de otra unidad o de un período fuera de su residencia
- **THEN** la descarga responde 404
