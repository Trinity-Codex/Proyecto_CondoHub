## MODIFIED Requirements

### Requirement: Confirmación de lectura
El sistema SHALL permitir que un residente al que va dirigido un comunicado lo marque como leído una sola vez, guardando la fecha y hora, y SHALL mostrar al administrador cuántas de las unidades destinatarias con residentes activos confirmaron la lectura. El conteo MUST ser por unidad: una unidad cuenta como confirmada si cualquiera de sus residentes activos marcó el comunicado. El sistema SHALL mostrar además al administrador y al comité qué residentes confirmaron, con fecha y hora, y cuáles no; un residente MUST ver solo su propio estado.

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
- **THEN** ve los residentes destinatarios que confirmaron, con fecha y hora, y los que aún no

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente de otro edificio intenta marcar como leído, o un residente o conserje abre la lectura por residente
- **THEN** el sistema responde 403 o 404; solo el administrador ve el conteo por unidad y solo administrador y comité ven la lectura por residente

## ADDED Requirements

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
