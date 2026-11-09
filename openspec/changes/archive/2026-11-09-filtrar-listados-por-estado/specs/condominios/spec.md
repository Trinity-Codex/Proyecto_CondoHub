## ADDED Requirements

### Requirement: Filtro de unidades por ocupación
El sistema SHALL filtrar el listado de unidades con `?ocupacion=con_residentes|sin_residentes` (con residentes activos, el mismo criterio de «Con residencia vigente» del panel de inicio) y mostrar chips con la cantidad de unidades de cada grupo, contadas sobre las unidades del condominio activo. El orden (edificio, piso, número) se mantiene. Solo administrador y comité pueden abrirlo.

#### Scenario: Unidades sin residentes
- **WHEN** el administrador abre `?ocupacion=sin_residentes`
- **THEN** cada edificio muestra solo sus unidades sin residentes activos y los chips cuentan ambos grupos

#### Scenario: Cuadra con el panel
- **WHEN** se suman las unidades «Con residentes» de los chips
- **THEN** el resultado coincide con las unidades que tienen algún residente activo y el panel cuenta los mismos residentes

#### Scenario: Aislamiento y acceso
- **WHEN** otro condominio tiene unidades, o un conserje o residente abre el listado
- **THEN** ninguna cantidad incluye lo ajeno y el conserje y el residente reciben 403
