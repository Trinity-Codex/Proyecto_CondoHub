## ADDED Requirements

### Requirement: Operación en producción
La instancia pública SHALL atender solo por HTTPS, con cookies de sesión y CSRF seguras, y MUST NOT mostrar detalles
técnicos en las páginas de error. Las credenciales (clave de Django, base de datos y correo) MUST venir de la
configuración del servicio y nunca del repositorio; sin clave secreta, la instancia MUST NOT arrancar. Las
invitaciones y la recuperación de contraseña SHALL llegar por correo real, y los PDF SHALL incluir su logo.

#### Scenario: Visita por HTTP
- **WHEN** alguien abre la URL pública con `http://`
- **THEN** el sistema lo redirige a la misma dirección con `https://`

#### Scenario: Error sin detalles técnicos
- **WHEN** una página de la instancia pública falla
- **THEN** el visitante ve la página de error de CondoHub, sin código ni configuración

#### Scenario: Arranque sin clave secreta
- **WHEN** la instancia de producción arranca sin clave secreta configurada
- **THEN** no atiende solicitudes y el registro del servicio indica la variable que falta

#### Scenario: Revisión de seguridad de Django
- **WHEN** se ejecuta `python manage.py check --deploy` con la configuración de producción
- **THEN** no aparece ninguna advertencia

#### Scenario: Recuperar contraseña en la instancia pública
- **WHEN** un usuario pide recuperar su contraseña en la URL pública
- **THEN** recibe el correo en su bandeja, con un enlace `https://` a la URL pública

#### Scenario: Acceso por rol en producción
- **WHEN** un visitante sin sesión abre una página interna, o un residente abre una página del administrador
- **THEN** el primero va al inicio de sesión y el segundo ve "No tienes permisos" (403), igual que en desarrollo

### Requirement: Límite de intentos detrás del proxy
Cuando el servicio pone uno o más proxies delante de la aplicación, el límite de intentos de inicio de sesión SHALL
contar los fallos por la dirección real de cada visitante, sin el puerto de la conexión, y MUST ignorar las
direcciones que el visitante agregue por su cuenta a la cabecera de reenvío. La cantidad de proxies confiables
SHALL definirse en la configuración del servicio.

#### Scenario: Una persona bloqueada no bloquea a otra
- **WHEN** un residente falla 5 veces el inicio de sesión y, desde otra red, el administrador ingresa su clave correcta
- **THEN** el residente queda bloqueado y el administrador entra a su panel

#### Scenario: Puerto distinto en cada intento
- **WHEN** la misma persona falla 5 veces y el proxy reenvía su dirección con un puerto distinto cada vez
- **THEN** el sexto intento desde esa dirección queda bloqueado

#### Scenario: Dirección falsificada
- **WHEN** un visitante envía una cabecera de reenvío con una dirección inventada a la izquierda de la real
- **THEN** el sistema cuenta el intento con la dirección real

### Requirement: Demo pública con clave privada
La instancia pública SHALL tener los datos de demostración desde el primer despliegue, y los despliegues siguientes
MUST NOT borrar ni duplicar datos. Las cuentas demo de la instancia pública MUST usar una clave privada definida en
la configuración del servicio, distinta de la que publica el README.

#### Scenario: Primer despliegue
- **WHEN** se despliega por primera vez sobre una base vacía
- **THEN** quedan las tablas creadas y los dos condominios demo con un usuario por rol

#### Scenario: Despliegue siguiente
- **WHEN** se despliega una versión nueva sobre una base con datos
- **THEN** se aplican las migraciones pendientes y los datos existentes, incluidos los creados por los usuarios, siguen iguales

#### Scenario: Clave del README en la instancia pública
- **WHEN** alguien intenta entrar como el administrador demo con la clave publicada en el README
- **THEN** el sistema rechaza el ingreso, y con la clave privada el administrador entra y el residente demo ve solo su cuenta
