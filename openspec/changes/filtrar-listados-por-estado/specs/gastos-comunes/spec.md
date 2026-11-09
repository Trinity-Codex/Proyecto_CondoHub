## ADDED Requirements

### Requirement: Filtro de egresos por categoría
El sistema SHALL filtrar los egresos de un período con `?categoria=<categoría>` y mostrar chips con la cantidad de egresos de cada categoría del período, ordenados del más reciente al más antiguo. Administrador y comité ven el listado; el filtro no da acceso a períodos de otro condominio.

#### Scenario: Egresos de una categoría
- **WHEN** el comité abre el período con `?categoria=` de una categoría que tiene egresos
- **THEN** ve solo esos egresos, el total del período sigue siendo el de todos y los chips cuentan todas las categorías

#### Scenario: Período de otro condominio
- **WHEN** alguien abre por URL el período de otro condominio con un filtro
- **THEN** el sistema responde 404
