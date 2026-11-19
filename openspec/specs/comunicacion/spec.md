# comunicacion Specification

## Purpose
Publicar comunicados oficiales y avisar automáticamente a cada persona de lo que le concierne, en el
sitio y por correo (RF09, RF10, RF13, RF23). Código: `apps/comunicados`, `apps/notificaciones`.

## Requirements

### Requirement: Comunicados generales o por edificio
El sistema SHALL permitir que el administrador publique, edite, fije y elimine comunicados dirigidos a todo el condominio o a un edificio.

#### Scenario: Comunicado fijado
- **WHEN** el administrador fija un comunicado
- **THEN** aparece primero en la lista

### Requirement: Visibilidad de comunicados
El sistema SHALL mostrar a administrador, comité y conserje todos los comunicados del condominio, y al residente solo los generales y los dirigidos a los edificios donde vive, en la lista, el detalle y el panel de inicio. Un comunicado con fecha «Visible hasta» anterior a hoy SHALL salir de la lista principal y del panel de inicio, y SHALL seguir disponible en la lista de vencidos y en su detalle para quien puede verlo.

#### Scenario: Comunicado de otro edificio
- **WHEN** un residente del edificio A abre por URL directa un comunicado dirigido al edificio B
- **THEN** el sistema responde 404

#### Scenario: Comunicado vencido
- **WHEN** la fecha «Visible hasta» de un comunicado ya pasó
- **THEN** no aparece en la lista principal ni en el panel de inicio, aparece en «Ver vencidos» con la insignia «Vencido» y su detalle se sigue abriendo

#### Scenario: Comunicado sin fecha de vigencia
- **WHEN** un comunicado no tiene fecha «Visible hasta»
- **THEN** sigue en la lista principal indefinidamente

#### Scenario: Fecha de vigencia pasada al publicar
- **WHEN** el administrador publica un comunicado con una fecha «Visible hasta» anterior a hoy
- **THEN** el formulario rechaza la fecha

### Requirement: Notificaciones automáticas
El sistema SHALL notificar (patrón Observer) la publicación de comunicados, los cambios de estado de incidentes, la emisión de gastos comunes y el registro de pagos a las personas afectadas, en la campana del menú y por correo a quienes aceptan recibir correos. El correo de un comunicado SHALL llevar en el asunto su título y un enlace directo a él, sin datos de otros residentes.

#### Scenario: Persona que no recibe correos
- **WHEN** se publica un comunicado y un residente tiene desactivado "recibir correos"
- **THEN** recibe la notificación en el sitio y no recibe correo

#### Scenario: Correo de un comunicado
- **WHEN** se publica un comunicado
- **THEN** el correo tiene el asunto «Nuevo comunicado: <título>» («Aviso importante: <título>» si es prioritario) y un enlace que, tras iniciar sesión, lleva a ese comunicado

### Requirement: Enlaces seguros
El sistema SHALL abrir desde una notificación solo direcciones del propio sitio.

#### Scenario: Enlace externo
- **WHEN** una notificación o un parámetro "volver" contiene una dirección de otro sitio
- **THEN** el sistema redirige a una página interna segura

### Requirement: Recordatorios de pago
El sistema SHALL ofrecer un comando que avise por la campana y por correo (patrón Observer) a cada residente con saldo en un período emitido, una vez en los 3 días previos al vencimiento y una vez entre 1 y 7 días después. El sistema MUST NOT avisar dos veces lo mismo, ni a quien ya pagó, ni a residentes fuera de su período de residencia.

#### Scenario: Aviso antes del vencimiento
- **WHEN** el comando corre 3 días antes del vencimiento y un residente tiene saldo en ese período
- **THEN** el residente recibe en la campana y por correo cuánto debe y cuándo vence, con enlace a su cobro

#### Scenario: Aviso después del vencimiento
- **WHEN** el comando corre el día siguiente al vencimiento y el residente sigue con saldo
- **THEN** recibe un aviso de que el cobro venció

#### Scenario: Sin repetir
- **WHEN** el comando corre dos veces el mismo día, o en dos días seguidos antes del vencimiento
- **THEN** el residente recibe ese aviso una sola vez

#### Scenario: Ya pagó
- **WHEN** el cobro del residente está pagado
- **THEN** no recibe aviso

#### Scenario: Fuera de su período
- **WHEN** el residente llegó a la unidad después del mes del período, o fue dado de baja
- **THEN** no recibe aviso de ese cobro

#### Scenario: Persona que no recibe correos
- **WHEN** un residente con saldo tiene desactivado "recibir correos"
- **THEN** recibe el aviso en el sitio y no recibe correo

#### Scenario: Acceso por rol
- **WHEN** cualquier persona intenta ejecutar los recordatorios desde el sitio
- **THEN** no existe una página para hacerlo: solo se ejecutan con el comando en el servidor

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

### Requirement: Aviso prioritario
El sistema SHALL permitir que el administrador marque un comunicado como prioritario, con fecha «Visible hasta» obligatoria. Mientras un aviso prioritario esté vigente y dirigido a un residente que no lo confirmó, el sistema MUST llevar a ese residente a una pantalla completa con el aviso desde cualquier página, hasta que pulse «He leído este aviso». Cerrar sesión MUST seguir disponible, y un error al revisar los avisos MUST NOT bloquear al residente.

#### Scenario: Bloqueo hasta confirmar
- **WHEN** un residente con un aviso prioritario vigente sin confirmar abre cualquier página, también escribiendo otra URL
- **THEN** es llevado a la pantalla del aviso y no puede seguir hasta confirmarlo

#### Scenario: Confirmación registrada
- **WHEN** el residente pulsa «He leído este aviso»
- **THEN** queda registrada la fecha y hora, el aviso no vuelve a aparecerle y vuelve a la página que había pedido

#### Scenario: Varios avisos
- **WHEN** el residente tiene varios avisos prioritarios pendientes
- **THEN** se muestran de a uno, por orden de publicación

#### Scenario: Aviso vencido o comunicado normal
- **WHEN** el aviso venció o el comunicado no es prioritario
- **THEN** no bloquea a nadie

#### Scenario: Solo el rol residente
- **WHEN** un administrador, un miembro del comité o un conserje navega con un aviso prioritario vigente
- **THEN** navega normal, aunque además viva en el condominio

#### Scenario: Aviso dirigido a un edificio
- **WHEN** el aviso es solo para un edificio
- **THEN** bloquea únicamente a los residentes de ese edificio y nunca a los de otro condominio

#### Scenario: Prioritario sin fecha
- **WHEN** el administrador marca un comunicado como prioritario sin «Visible hasta»
- **THEN** el formulario lo rechaza con un mensaje claro

#### Scenario: Falla abierta
- **WHEN** la revisión de avisos pendientes falla por un error
- **THEN** el residente sigue navegando y el error queda registrado

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
