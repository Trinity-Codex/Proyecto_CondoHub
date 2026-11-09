## ADDED Requirements

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
