# Spec Delta

## ADDED Requirements

### Requirement: Indicadores de cobranza
El sistema SHALL mostrar en el panel de inicio del administrador y del comité, para el último período emitido del condominio activo, el porcentaje de recaudación, la deuda total y la cantidad de unidades morosas, con los mismos números del reporte de recaudación y morosidad y un enlace a él.

#### Scenario: Indicadores del último período
- **WHEN** el administrador abre el inicio y hay períodos emitidos
- **THEN** ve el porcentaje de recaudación, la deuda total y las unidades morosas del último período emitido, iguales a las del reporte

#### Scenario: Sin períodos emitidos
- **WHEN** el condominio aún no emite gastos comunes
- **THEN** el panel indica que todavía no hay indicadores

#### Scenario: Acceso por rol
- **WHEN** un conserje o un residente abre el inicio
- **THEN** no ve los indicadores de cobranza
