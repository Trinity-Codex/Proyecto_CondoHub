## MODIFIED Requirements

### Requirement: Notificaciones automáticas
El sistema SHALL notificar (patrón Observer) la publicación de comunicados, los cambios de estado de incidentes, la emisión de gastos comunes y el registro de pagos a las personas afectadas, en la campana del menú y por correo a quienes aceptan recibir correos. El correo de un comunicado SHALL llevar en el asunto su título y un enlace directo a él, sin datos de otros residentes.

#### Scenario: Persona que no recibe correos
- **WHEN** se publica un comunicado y un residente tiene desactivado "recibir correos"
- **THEN** recibe la notificación en el sitio y no recibe correo

#### Scenario: Correo de un comunicado
- **WHEN** se publica un comunicado
- **THEN** el correo tiene el asunto «Nuevo comunicado: <título>» («Aviso importante: <título>» si es prioritario) y un enlace que, tras iniciar sesión, lleva a ese comunicado

### Requirement: Confirmación de lectura
El sistema SHALL permitir que un residente al que va dirigido un comunicado lo marque como leído una sola vez, con fecha y hora, y SHALL mostrar al administrador cuántas unidades destinatarias confirmaron; una unidad MUST contar si cualquiera de sus residentes activos lo marcó. Administrador y comité SHALL ver qué residentes confirmaron, cuándo y el porcentaje de lectura; un residente MUST ver solo su propio estado.

#### Scenario: El residente marca como leído
- **WHEN** un residente abre un comunicado dirigido a él y pulsa «Marcar como leído»
- **THEN** queda registrado y el detalle le muestra «Leíste este comunicado» en lugar del botón

#### Scenario: Conteo por unidad
- **WHEN** dos residentes de la misma unidad marcan el comunicado como leído
- **THEN** el administrador ve esa unidad una sola vez entre las que confirmaron

#### Scenario: Unidades que faltan
- **WHEN** el administrador abre el detalle de un comunicado
- **THEN** ve «Unidades que confirmaron la lectura: X de Y» y la lista de unidades que aún no lo hacen

#### Scenario: Lectura por residente
- **WHEN** el administrador o un miembro del comité abre la lectura de un comunicado
- **THEN** ve los residentes destinatarios que confirmaron, con fecha y hora, los que aún no, y el porcentaje de lectura por residente y por unidad

#### Scenario: Contador del residente
- **WHEN** un residente tiene comunicados vigentes dirigidos a él sin leer
- **THEN** ve su cantidad junto a «Comunicados» en el menú, que baja al leerlos y nunca cuenta comunicados de otro edificio u otro condominio

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente de otro edificio intenta marcar como leído, o un residente o conserje abre la lectura por residente
- **THEN** el sistema responde 403 o 404; solo el administrador ve el conteo por unidad y solo administrador y comité ven la lectura por residente

## ADDED Requirements

### Requirement: Recordatorio de comunicados sin leer
El sistema SHALL recordar, por la campana y por correo, a cada residente destinatario que no leyó un comunicado vigente cuando pasan N días desde su publicación, con N configurable por el administrador de cada condominio (por defecto 3). El recordatorio MUST enviarse una sola vez por persona y comunicado.

#### Scenario: Recordatorio a quien no leyó
- **WHEN** se ejecuta el comando de recordatorios después del plazo de un comunicado vigente
- **THEN** solo los residentes destinatarios que no lo leyeron reciben un recordatorio, y no el comité ni quien ya lo leyó

#### Scenario: Sin repetir
- **WHEN** el comando se ejecuta otra vez, el mismo u otro día
- **THEN** no envía un segundo recordatorio a la misma persona por el mismo comunicado

#### Scenario: Plazo del condominio
- **WHEN** el administrador cambia el plazo a un valor entre 1 y 30 días
- **THEN** los recordatorios de su condominio usan ese plazo; otros roles reciben 403 en esa pantalla

#### Scenario: Comunicados que no se recuerdan
- **WHEN** el comunicado venció, aún no cumple el plazo o lo cumplió hace más de una semana, o la cuenta está inactiva
- **THEN** no se envía recordatorio
