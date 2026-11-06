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
