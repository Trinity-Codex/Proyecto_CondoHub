# pagos Specification

## Purpose
Mostrar a cada residente lo que debe y registrar los pagos de cada cobro, totales o parciales
(RF03, RF04). Código: `apps/pagos` (`consultas.py`, `models.py`).

## Requirements

### Requirement: Estado de cuenta del residente
El sistema SHALL mostrar en "Mi cuenta" los cobros de las unidades donde la persona es residente activa, con lo pagado y el saldo de cada uno, y el detalle de cada cobro.

#### Scenario: Residente al día
- **WHEN** un residente cuyos cobros están todos pagados abre Mi cuenta
- **THEN** ve saldo cero

#### Scenario: Cobro de otra unidad
- **WHEN** un residente abre por URL directa el cobro de una unidad que no es suya
- **THEN** el sistema responde 404

### Requirement: Cobranza por unidad
El sistema SHALL mostrar al administrador y al comité la deuda de cada unidad del condominio activo y la cuenta completa de cada unidad.

#### Scenario: Comité consulta la cobranza
- **WHEN** un miembro del comité abre la cobranza
- **THEN** ve la deuda por unidad y no puede registrar pagos

### Requirement: Registro de pagos
El sistema SHALL permitir que el administrador registre pagos de un cobro con fecha, monto, medio (transferencia, efectivo, cheque o Webpay como etiqueta) y observación; MUST impedir pagos que superen el saldo, pagos a un cobro ya pagado y fechas futuras; y SHALL marcar el cobro como PAGADO cuando los pagos cubren el total.

#### Scenario: Abono parcial
- **WHEN** el administrador registra un pago menor que el saldo
- **THEN** el cobro sigue pendiente con el saldo restante y el residente recibe un aviso

#### Scenario: Pago en exceso
- **WHEN** el administrador registra un pago mayor que el saldo
- **THEN** el pago se rechaza indicando el saldo pendiente

#### Scenario: Pagos simultáneos
- **WHEN** llegan dos pagos simultáneos que juntos superan el saldo
- **THEN** solo se acepta el que cabe en el saldo
