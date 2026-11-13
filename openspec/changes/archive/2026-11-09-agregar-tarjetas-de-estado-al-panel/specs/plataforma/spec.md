# Spec Delta

## ADDED Requirements

### Requirement: Panel con tarjetas por estado
El sistema SHALL mostrar en el panel de inicio una tarjeta por estado, con nombre, cantidad y una frase, cuyo enlace entero lleva al listado correspondiente: unidades al día, con deuda y morosas, incidentes recibidos y en proceso, y reservas próximas. Las cantidades MUST salir solo del condominio activo, y las de unidades del reporte de cobranza, sin recalcular la morosidad.

#### Scenario: Cantidades del administrador
- **WHEN** el administrador abre el inicio de un condominio con unidades al día, con deuda y morosas, incidentes recibidos y en proceso, y reservas confirmadas desde hoy
- **THEN** cada tarjeta muestra su cantidad correcta y las tres de unidades suman las unidades del período; el comité ve las mismas seis tarjetas

#### Scenario: Aislamiento entre condominios
- **WHEN** otro condominio tiene incidentes, reservas y unidades con deuda
- **THEN** ninguna cantidad del panel los incluye

#### Scenario: Enlace de la tarjeta
- **WHEN** el administrador abre la tarjeta de incidentes en proceso
- **THEN** llega a la lista de incidentes filtrada por `?estado=EN_PROCESO`

#### Scenario: Conserje
- **WHEN** un conserje abre el inicio
- **THEN** ve las tarjetas de incidentes y reservas y ninguna de unidades ni de dinero

#### Scenario: Residente
- **WHEN** un residente abre el inicio
- **THEN** no ve tarjetas por estado y conserva las suyas

#### Scenario: Sin períodos emitidos
- **WHEN** el condominio aún no emite gastos comunes
- **THEN** el administrador no ve tarjetas de unidades y el panel conserva el aviso de que aún no hay indicadores

#### Scenario: Pantallas angostas y anchas
- **WHEN** el panel se abre a 375 px y a 1440 px
- **THEN** no hay desborde horizontal ni tarjetas solapadas, y desde 992 px las tarjetas se muestran de tres en tres (administrador y comité en dos filas, el conserje en una)

### Requirement: Colores por estado accesibles
El sistema SHALL definir un color por estado en variables CSS (`--estado-*`, con su fondo y su texto) que alcancen contraste AA (3:1 el acento, 4,5:1 el texto sobre su fondo), y MUST NOT usar el color como único indicador: toda tarjeta o etiqueta de estado lleva también su nombre en texto. Las tarjetas enlace SHALL tener nombre accesible y foco visible.

#### Scenario: Tarjeta como enlace
- **WHEN** una persona recorre el panel con el teclado
- **THEN** cada tarjeta recibe el foco con un contorno visible y su nombre accesible incluye el estado y la cantidad
