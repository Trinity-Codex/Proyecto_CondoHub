# reportes Specification

## Purpose
Entregar al administrador y al comité la recaudación y la morosidad de cada período emitido, con
descarga para Excel (RF11). Código: `apps/gastos/reportes.py`.

## Requirements

### Requirement: Reporte de recaudación y morosidad
El sistema SHALL generar, para un período emitido y opcionalmente un edificio, el total emitido, el total recaudado, el porcentaje de recaudación, el saldo y la deuda anterior de cada unidad, y SHALL marcar como morosa a la unidad con deuda de períodos anteriores.

#### Scenario: Deuda solo del mes
- **WHEN** una unidad debe solo el cobro del período del reporte
- **THEN** aparece con saldo, pero no como morosa

#### Scenario: Acceso del residente
- **WHEN** un residente intenta abrir el reporte
- **THEN** el sistema responde 403

### Requirement: Descarga en CSV segura
El sistema SHALL descargar el reporte en CSV para Excel y MUST neutralizar los textos que empiezan con `=`, `+`, `-`, `@`, tabulación o retorno de carro para que Excel no los ejecute como fórmula.

#### Scenario: Texto con fórmula
- **WHEN** una descripción del reporte empieza con un signo igual
- **THEN** el CSV la escribe como texto, sin que Excel la evalúe

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

### Requirement: Filtro del reporte por situación de la unidad
El sistema SHALL filtrar la tabla del reporte de recaudación y su descarga CSV con `?situacion=al_dia|pendiente|morosa` (la `situacion` de cada fila: «Al día», «Pendiente», «Morosa»), mostrar chips con la cantidad de unidades de cada situación del período y edificio elegidos, y ordenar la tabla con las morosas primero, luego las pendientes y al final las al día, de mayor a menor deuda total. Los totales siguen siendo los de todas las unidades y la regla de morosidad no cambia.

#### Scenario: Enlace desde el panel
- **WHEN** el administrador abre la tarjeta «Unidades morosas» del inicio
- **THEN** llega al reporte con `?periodo=<pk>&situacion=morosa`, la tabla muestra solo las morosas y la cantidad coincide con la tarjeta

#### Scenario: Situación inválida
- **WHEN** se abre el reporte con `?situacion=xyz`
- **THEN** se muestran todas las unidades, sin error

#### Scenario: Descarga filtrada
- **WHEN** se descarga el CSV con `?situacion=pendiente`
- **THEN** el archivo trae solo las unidades pendientes

#### Scenario: Acceso del residente
- **WHEN** un residente o un conserje abre el reporte con `?situacion=morosa`
- **THEN** el sistema responde 403
