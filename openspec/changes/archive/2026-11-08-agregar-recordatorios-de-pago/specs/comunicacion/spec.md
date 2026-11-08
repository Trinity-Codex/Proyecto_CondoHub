# Spec Delta

## ADDED Requirements

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
