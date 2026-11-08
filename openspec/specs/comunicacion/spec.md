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
El sistema SHALL mostrar a administrador, comité y conserje todos los comunicados del condominio, y al residente solo los generales y los dirigidos a los edificios donde vive, en la lista, el detalle y el panel de inicio.

#### Scenario: Comunicado de otro edificio
- **WHEN** un residente del edificio A abre por URL directa un comunicado dirigido al edificio B
- **THEN** el sistema responde 404

### Requirement: Notificaciones automáticas
El sistema SHALL notificar (patrón Observer) la publicación de comunicados, los cambios de estado de incidentes, la emisión de gastos comunes y el registro de pagos a las personas afectadas, en la campana del menú y por correo a quienes aceptan recibir correos.

#### Scenario: Persona que no recibe correos
- **WHEN** se publica un comunicado y un residente tiene desactivado "recibir correos"
- **THEN** recibe la notificación en el sitio y no recibe correo

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
