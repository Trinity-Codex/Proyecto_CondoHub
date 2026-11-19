## ADDED Requirements

### Requirement: Saldo del fondo en el aviso de cobro
El aviso SHALL mostrar el saldo contable del fondo de reserva del condominio al cierre del mes según su libro de movimientos.

#### Scenario: Período sin historia contable suficiente
- **WHEN** el período no tiene cobertura del libro del fondo
- **THEN** el aviso y la rendición indican que el histórico no está disponible

#### Scenario: Saldo disponible
- **WHEN** un período dispone de cobertura contable
- **THEN** el saldo de fondo del aviso coincide con el de la rendición
