## ADDED Requirements

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
