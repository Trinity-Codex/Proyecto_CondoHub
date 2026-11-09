# Spec Delta

## MODIFIED Requirements

### Requirement: Indicadores de cobranza
El sistema SHALL mostrar en la página Cobranza del administrador y del comité, para el último período emitido del condominio activo, el porcentaje de recaudación y la deuda al cierre del período con un enlace al reporte de recaudación y morosidad, junto a la deuda total del condominio, y en el panel de inicio la cantidad de unidades al día, con deuda y morosas en tarjetas por estado, con los mismos números del reporte.

#### Scenario: Indicadores del último período
- **WHEN** el administrador abre la página Cobranza y hay períodos emitidos
- **THEN** ve el porcentaje de recaudación y la deuda al cierre del último período emitido, iguales a las del reporte, y la deuda total del condominio, sobre la tabla de unidades; en el inicio ve las unidades al día, con deuda y morosas en sus tarjetas

#### Scenario: Sin períodos emitidos
- **WHEN** el condominio aún no emite gastos comunes
- **THEN** la página Cobranza indica que todavía no hay indicadores del período, muestra la deuda total del condominio y conserva la tabla

#### Scenario: Acceso por rol
- **WHEN** un conserje o un residente intenta abrir la página Cobranza o el inicio
- **THEN** no ve los indicadores de cobranza ni las tarjetas de unidades
