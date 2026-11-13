# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité o un residente intenta registrar un pago
- **THEN** el sistema responde 403 y no se crea ningún pago
