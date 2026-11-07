# Spec Delta

## MODIFIED Requirements

### Requirement: Inicio de sesión con correo
El sistema SHALL identificar a cada persona por su correo electrónico y exigir inicio de sesión para todas las páginas, salvo las de acceso y recuperación. MUST bloquear temporalmente el ingreso tras 5 intentos fallidos en 15 minutos con el mismo correo o desde la misma dirección, tanto en el sitio como en el panel de administración, sin revelar si el correo existe.

#### Scenario: Ingreso correcto
- **WHEN** una persona activa ingresa su correo y su contraseña correctos
- **THEN** entra al panel de inicio del condominio activo

#### Scenario: Página protegida sin sesión
- **WHEN** una persona sin sesión abre cualquier página interna
- **THEN** el sistema la redirige al inicio de sesión

#### Scenario: Quinto intento fallido con el mismo correo
- **WHEN** alguien falla 5 veces en 15 minutos con el mismo correo, aunque cambie de dirección o de mayúsculas
- **THEN** el sistema bloquea ese correo y muestra cómo recuperar la contraseña

#### Scenario: Quinto intento fallido desde la misma dirección
- **WHEN** alguien falla 5 veces en 15 minutos desde la misma dirección, con correos distintos
- **THEN** el sistema bloquea el ingreso desde esa dirección

#### Scenario: Clave correcta durante el bloqueo
- **WHEN** una persona bloqueada ingresa su contraseña correcta
- **THEN** el sistema no la deja entrar y muestra el mismo mensaje de bloqueo

#### Scenario: El mensaje no revela si el correo existe
- **WHEN** se llega al bloqueo con un correo registrado y con uno que no existe
- **THEN** el mensaje es idéntico en ambos casos

#### Scenario: El bloqueo termina con el tiempo
- **WHEN** pasan 15 minutos y los intentos fallidos salen de la ventana
- **THEN** la persona puede volver a ingresar sin ninguna acción del administrador

#### Scenario: Ingreso correcto antes del límite
- **WHEN** una persona falla menos de 5 veces y luego ingresa correctamente
- **THEN** sus intentos fallidos se borran y vuelve a tener 5 intentos

#### Scenario: Recuperar la contraseña durante el bloqueo
- **WHEN** una persona bloqueada por los intentos de su correo define una contraseña nueva con el enlace del correo
- **THEN** los intentos de su cuenta se borran y puede ingresar de inmediato

#### Scenario: Dirección bloqueada por otros correos
- **WHEN** una persona define una contraseña nueva, pero su dirección llegó al límite con fallos de otros correos
- **THEN** sigue bloqueada desde esa dirección hasta que los intentos salgan de la ventana

#### Scenario: Panel de administración
- **WHEN** alguien falla 5 veces en el inicio de sesión de `/admin/`
- **THEN** el sistema aplica el mismo bloqueo

### Requirement: RUT validado
El sistema SHALL validar el formato y el dígito verificador de todo RUT ingresado, y MUST impedir en el alta de usuarios y en Mi perfil que una persona use un RUT que ya tiene otra cuenta.

#### Scenario: Dígito verificador incorrecto
- **WHEN** se guarda un RUT con dígito verificador incorrecto
- **THEN** el formulario muestra "El dígito verificador del RUT no es correcto." y no guarda

#### Scenario: RUT de otra persona
- **WHEN** en el alta o en Mi perfil se ingresa un RUT que ya tiene otra cuenta, con o sin puntos
- **THEN** el formulario muestra "Ya existe otra cuenta con ese RUT." y no guarda

#### Scenario: Conservar el propio RUT
- **WHEN** una persona guarda Mi perfil con su propio RUT
- **THEN** el sistema lo acepta

### Requirement: Alta de usuarios por invitación
El sistema SHALL permitir que el administrador cree la cuenta de una persona con su rol en el condominio activo y le envíe una invitación por correo para definir su contraseña, válida por 72 horas.

#### Scenario: Invitación enviada
- **WHEN** el administrador da de alta a una persona con su correo y rol
- **THEN** se crea la cuenta con una contraseña aleatoria que nadie conoce, se crea su membresía y se envía el correo de invitación
