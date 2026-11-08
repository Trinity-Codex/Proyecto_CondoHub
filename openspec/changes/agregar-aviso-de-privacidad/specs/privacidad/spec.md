# Spec Delta

## Purpose

Informar a cada persona cómo CondoHub trata sus datos personales y permitirle ejercer sus derechos sobre ellos, según la Ley 21.719 (RF22). Código: `apps/privacidad`.

## ADDED Requirements

### Requirement: Aviso de privacidad
El sistema SHALL publicar, sin exigir sesión, un aviso que indique qué datos personales se tratan y para qué, quién es responsable y quién encargado, cuánto tiempo se conservan, cómo ejercer los derechos de acceso, rectificación, supresión y oposición, y que la instancia usa datos de demostración. El aviso MUST estar enlazado desde el inicio de sesión y el pie de página.

#### Scenario: Lectura sin sesión
- **WHEN** una persona sin sesión abre el aviso desde el enlace del inicio de sesión
- **THEN** lo lee completo, incluida la advertencia de datos de demostración

#### Scenario: Acceso por rol
- **WHEN** un administrador, un miembro del comité, un conserje o un residente abre el aviso
- **THEN** el sistema lo muestra a todos, sin datos de ningún condominio

### Requirement: Solicitudes del titular
El sistema SHALL permitir que una persona con sesión presente una solicitud de acceso, rectificación, supresión u oposición en su condominio activo, y que el administrador de ese condominio la responda y la cierre. Cada solicitud MUST guardar fecha, tipo, estado y respuesta, y avisar al administrador al llegar y a la persona al cerrarse.

#### Scenario: Presentar una solicitud
- **WHEN** un residente envía una solicitud de rectificación con su detalle
- **THEN** queda pendiente con su fecha y tipo, el residente la ve en su lista y el administrador recibe un aviso

#### Scenario: Responder y cerrar
- **WHEN** el administrador responde una solicitud pendiente de su condominio
- **THEN** la solicitud queda cerrada con la respuesta y la fecha de cierre, y la persona recibe un aviso

#### Scenario: Solo las propias solicitudes
- **WHEN** un residente abre por URL directa la solicitud de otra persona
- **THEN** el sistema responde 404

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente intenta ver la lista de solicitudes del condominio o responder una
- **THEN** el sistema responde 403

#### Scenario: Solicitud de otro condominio
- **WHEN** el administrador abre por URL directa una solicitud de un condominio que no administra
- **THEN** el sistema responde 404

### Requirement: Descarga de mis datos
El sistema SHALL permitir que una persona con sesión descargue desde Mi perfil un archivo en formato JSON con los datos de su cuenta y lo vinculado a ella en sus condominios: roles, residencias, reservas, incidentes, solicitudes, notificaciones y cobros, estos últimos solo de su período de residencia.

#### Scenario: Descargar mis datos
- **WHEN** un residente descarga sus datos
- **THEN** recibe un archivo JSON con su cuenta, su residencia y sus cobros visibles, sin la contraseña

#### Scenario: Cobros de antes de su llegada
- **WHEN** un residente llegado en marzo descarga sus datos y su unidad tiene una deuda de febrero
- **THEN** el archivo no incluye el cobro de febrero

#### Scenario: Acceso por rol
- **WHEN** una persona sin sesión intenta descargar datos
- **THEN** el sistema la redirige al inicio de sesión, y cualquier persona con sesión descarga solo los suyos
