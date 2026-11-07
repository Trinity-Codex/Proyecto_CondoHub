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
