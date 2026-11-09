# Spec Delta

## MODIFIED Requirements

### Requirement: Indicadores de cobranza
El sistema SHALL mostrar en el panel de inicio del administrador y del comité, para el último período emitido del condominio activo, el porcentaje de recaudación y la deuda total con un enlace al reporte de recaudación y morosidad, y la cantidad de unidades morosas, con la de unidades al día y con deuda, en tarjetas por estado, con los mismos números del reporte.

#### Scenario: Indicadores del último período
- **WHEN** el administrador abre el inicio y hay períodos emitidos
- **THEN** ve el porcentaje de recaudación y la deuda total del último período emitido, y las unidades morosas, con deuda y al día en sus tarjetas, iguales a las del reporte

#### Scenario: Sin períodos emitidos
- **WHEN** el condominio aún no emite gastos comunes
- **THEN** el panel indica que todavía no hay indicadores

#### Scenario: Acceso por rol
- **WHEN** un conserje o un residente abre el inicio
- **THEN** no ve los indicadores de cobranza
