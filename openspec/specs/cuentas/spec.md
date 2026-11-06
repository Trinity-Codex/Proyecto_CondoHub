# cuentas Specification

## Purpose
Identificar a las personas que usan CondoHub y administrar sus cuentas: inicio de sesión con correo,
RUT chileno, alta por invitación, recuperación de contraseña y perfil (RF12, RNF02). Código: `apps/cuentas`.

## Requirements

### Requirement: Inicio de sesión con correo
El sistema SHALL identificar a cada persona por su correo electrónico y exigir inicio de sesión para todas las páginas, salvo las de acceso y recuperación.

#### Scenario: Ingreso correcto
- **WHEN** una persona activa ingresa su correo y su contraseña correctos
- **THEN** entra al panel de inicio del condominio activo

#### Scenario: Página protegida sin sesión
- **WHEN** una persona sin sesión abre cualquier página interna
- **THEN** el sistema la redirige al inicio de sesión

### Requirement: RUT validado
El sistema SHALL validar el formato y el dígito verificador de todo RUT ingresado y MUST impedir que dos cuentas tengan el mismo RUT.

#### Scenario: Dígito verificador incorrecto
- **WHEN** se guarda un RUT con dígito verificador incorrecto
- **THEN** el formulario muestra "El dígito verificador del RUT no es correcto." y no guarda

### Requirement: Alta de usuarios por invitación
El sistema SHALL permitir que el administrador cree la cuenta de una persona con su rol en el condominio activo y le envíe una invitación por correo para definir su contraseña, válida por 72 horas.

#### Scenario: Invitación enviada
- **WHEN** el administrador da de alta a una persona con su correo y rol
- **THEN** se crea la cuenta sin contraseña utilizable, se crea su membresía y se envía el correo de invitación

### Requirement: Recuperación de contraseña
El sistema SHALL permitir recuperar la contraseña mediante un enlace enviado al correo, sin revelar si el correo existe.

#### Scenario: Correo desconocido
- **WHEN** alguien pide recuperar la contraseña de un correo que no existe
- **THEN** ve el mismo mensaje de confirmación que con un correo registrado

### Requirement: Perfil y preferencia de correos
El sistema SHALL permitir que cada persona edite sus datos, cambie su contraseña y decida si recibe avisos por correo (`recibir_correos`).

#### Scenario: Desactivar los correos
- **WHEN** una persona desmarca "recibir correos" en Mi perfil
- **THEN** deja de recibir avisos por correo y sigue recibiéndolos en el sitio
