# Spec Delta

## ADDED Requirements

### Requirement: Calendario de mantenciones
El sistema SHALL llevar por condominio un calendario de mantenciones periódicas, con su estado (al día, por vencer o vencida) calculado con la fecha de hoy. Al registrar una ejecución, la próxima fecha MUST ser la de ejecución más la frecuencia en meses. Solo el administrador SHALL escribir; comité y conserje ven y el residente recibe 403. Cada alta, cambio y ejecución MUST quedar en auditoría.

#### Scenario: Estados según la fecha de hoy
- **WHEN** hoy es el 16-nov-2026 y hay mantenciones con próxima fecha el 10-nov, el 25-nov y el 31-dic, todas con anticipación de 15 días
- **THEN** la del 10-nov aparece como «Vencida», la del 25-nov como «Por vencer» y la del 31-dic como «Al día»

#### Scenario: Anticipación configurable
- **WHEN** el administrador crea una mantención que vence en 30 días con anticipación de 30 días
- **THEN** aparece como «Por vencer», y con la anticipación por defecto de 15 días aparecería «Al día»

#### Scenario: Orden por urgencia
- **WHEN** el administrador abre el calendario con mantenciones vencidas, por vencer y al día
- **THEN** ve primero las vencidas, de la más antigua a la más reciente, y luego las demás por próxima fecha, con un chip y una insignia de estado en cada una

#### Scenario: Próxima fecha al registrar una ejecución
- **WHEN** el administrador registra que una mantención mensual se hizo el 31-ene-2028
- **THEN** su próxima fecha pasa al 29-feb-2028

#### Scenario: Ejecución anual en año bisiesto
- **WHEN** el administrador registra que una mantención anual se hizo el 29-feb-2028
- **THEN** su próxima fecha pasa al 28-feb-2029

#### Scenario: Ejecución con fecha futura
- **WHEN** el administrador intenta registrar una ejecución con una fecha posterior a hoy
- **THEN** el sistema la rechaza y la próxima fecha no cambia

#### Scenario: Administrador gestiona las mantenciones
- **WHEN** el administrador crea, edita o registra una ejecución de una mantención de su condominio
- **THEN** el cambio se guarda y queda un registro de auditoría con su usuario y los valores que cambiaron

#### Scenario: Comité o conserje intentan escribir
- **WHEN** un miembro del comité o un conserje abre el calendario
- **THEN** lo ve sin botones para crear, editar ni registrar ejecuciones, y si intenta esas rutas recibe 403

#### Scenario: Residente abre el calendario
- **WHEN** un residente abre el calendario de mantenciones
- **THEN** ve la página "No tienes permisos" (403)

#### Scenario: Mantención de otro condominio
- **WHEN** el administrador de un condominio abre el calendario o intenta editar o registrar una ejecución de una mantención de otro condominio
- **THEN** no ve sus datos y recibe 404 al intentar editarla o ejecutarla, y tampoco puede elegir un proveedor de otro condominio

#### Scenario: El calendario no afirma obligaciones legales
- **WHEN** cualquier rol con acceso abre el calendario
- **THEN** el texto aclara que cada condominio define qué mantenciones lleva y con qué frecuencia, sin presentarlas como obligaciones legales
