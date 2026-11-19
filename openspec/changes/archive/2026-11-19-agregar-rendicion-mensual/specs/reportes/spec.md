## ADDED Requirements

### Requirement: Rendición mensual al comité
El sistema SHALL mostrar y exportar en PDF la rendición de un período emitido del condominio activo para el administrador y el comité. Incluirá pagos vigentes, egresos con proveedor, caja, recaudación, morosidad, movimientos y saldo del fondo y pagos anulados con su motivo.

#### Scenario: Revisión mensual
- **WHEN** el comité descarga la rendición
- **THEN** la página y el PDF presentan los mismos importes, con caja por fecha de movimiento y recaudación por período del cobro

#### Scenario: Acceso fuera del alcance
- **WHEN** un residente consulta la rendición o su PDF
- **THEN** recibe 403

#### Scenario: Período ajeno o abierto
- **WHEN** el administrador consulta un período no emitido o de otro condominio
- **THEN** recibe 404
