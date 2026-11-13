# incidentes Specification

## Purpose
Reportar incidentes del condominio y seguir su atención (RF07, RF08). Código: `apps/incidentes`.

## Requirements

### Requirement: Reporte de incidentes
El sistema SHALL permitir que el residente reporte un incidente con categoría (mantención, seguridad, ruidos, aseo, áreas comunes u otro), título y descripción, que queda en estado RECIBIDO.

#### Scenario: Incidente nuevo
- **WHEN** un residente reporta un incidente
- **THEN** queda RECIBIDO y visible para la administración y la conserjería

### Requirement: Seguimiento por estados
El sistema SHALL permitir que el administrador y el conserje cambien el estado (RECIBIDO, EN_PROCESO, RESUELTO) y agreguen una respuesta, y SHALL notificar al residente que lo reportó.

#### Scenario: Incidente resuelto
- **WHEN** el conserje marca un incidente como RESUELTO con una respuesta
- **THEN** el residente recibe una notificación con el nuevo estado

### Requirement: Visibilidad de incidentes
El sistema SHALL mostrar al residente solo sus incidentes, y a administrador, comité y conserje todos los del condominio.

#### Scenario: Incidente ajeno
- **WHEN** un residente abre por URL directa el incidente de otra persona
- **THEN** el sistema responde 404

### Requirement: Filtro y orden de la lista de incidentes
El sistema SHALL filtrar la lista de incidentes con `?estado=RECIBIDO|EN_PROCESO|RESUELTO`, mostrar chips con la cantidad de cada estado sobre los incidentes que el rol puede ver, y ordenarla por urgencia: recibidos, luego en proceso y al final resueltos; dentro de los abiertos el más antiguo primero, y entre los resueltos el más reciente primero.

#### Scenario: Cantidades y filtro
- **WHEN** el administrador abre `?estado=EN_PROCESO` con incidentes en los tres estados
- **THEN** ve solo los en proceso y los chips muestran las cantidades de los tres estados

#### Scenario: Aislamiento
- **WHEN** otro condominio tiene incidentes en cualquier estado
- **THEN** ninguna cantidad ni fila los incluye

#### Scenario: Residente
- **WHEN** un residente abre la lista
- **THEN** los chips cuentan solo los incidentes que él reportó; un incidente ajeno no suma ni aparece

#### Scenario: Orden por urgencia
- **WHEN** hay un resuelto reciente y un recibido antiguo
- **THEN** el recibido aparece antes que el resuelto
