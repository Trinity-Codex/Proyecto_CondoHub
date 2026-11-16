# Spec Delta

## MODIFIED Requirements

### Requirement: Registro de pagos
El sistema SHALL permitir que el administrador registre pagos de un cobro con fecha, monto, medio (transferencia, efectivo, cheque o Webpay como etiqueta) y observación; MUST impedir pagos que superen el saldo, pagos a un cobro ya pagado y fechas futuras; SHALL marcar el cobro como PAGADO cuando los pagos cubren el total; y SHALL avisar del pago solo a los residentes activos que ven ese cobro.

#### Scenario: Abono parcial
- **WHEN** el administrador registra un pago menor que el saldo
- **THEN** el cobro sigue pendiente con el saldo restante y el residente recibe un aviso

#### Scenario: Pago en exceso
- **WHEN** el administrador registra un pago mayor que el saldo
- **THEN** el pago se rechaza indicando el saldo pendiente

#### Scenario: Pagos simultáneos
- **WHEN** llegan dos pagos simultáneos que juntos superan el saldo
- **THEN** solo se acepta el que cabe en el saldo

#### Scenario: Aviso solo a quien ve el cobro
- **WHEN** el administrador registra un pago de un cobro de febrero en una unidad donde un residente llegó en marzo y otro estaba desde febrero
- **THEN** solo el residente de febrero recibe el aviso, y el residente de marzo no recibe aviso ni enlace a ese cobro

#### Scenario: Residente dado de baja no recibe aviso
- **WHEN** el administrador registra un pago en una unidad donde una persona ya fue dado de baja
- **THEN** esa persona no recibe el aviso

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité o un residente intenta registrar un pago
- **THEN** el sistema responde 403 y no se crea ningún pago
