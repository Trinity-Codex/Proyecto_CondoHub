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
