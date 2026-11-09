## ADDED Requirements

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
