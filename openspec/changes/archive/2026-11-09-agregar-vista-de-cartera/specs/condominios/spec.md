## MODIFIED Requirements

### Requirement: Roles por condominio
El sistema SHALL asignar los roles administrador, comité, conserje y residente por condominio (membresía), de modo que una persona pueda tener roles distintos en condominios distintos. El superusuario actúa como administrador en todos. Además, solo el superusuario SHALL dar o quitar a una persona el acceso de administrador general sobre uno o más condominios: no es un rol de la membresía, solo permite consultar la cartera de esos condominios y MUST quedar en el registro de auditoría.

#### Scenario: Conserje sin datos financieros
- **WHEN** un conserje intenta abrir la cobranza o los gastos comunes
- **THEN** el sistema responde 403

#### Scenario: Asignar el acceso de administrador general
- **WHEN** el superusuario asigna el condominio A a una persona desde el panel de administración
- **THEN** la persona ve A en su cartera y el registro de auditoría de A guarda el cambio de rol, quién lo hizo y la persona afectada, sin su nombre ni su RUT

#### Scenario: Quitar el acceso de administrador general
- **WHEN** el superusuario quita el condominio A a un administrador general
- **THEN** A deja de aparecer en su cartera y el registro de auditoría de A guarda el cambio

#### Scenario: Sin rol dentro del condominio
- **WHEN** un administrador general sin membresía abre las unidades, los gastos comunes o la cobranza
- **THEN** el sistema no le muestra datos de ningún condominio y lo lleva a la cartera; su acceso no le da un condominio activo ni opciones en el selector de condominios

#### Scenario: Acceso por rol
- **WHEN** un administrador, un miembro del comité, un conserje, un residente o un administrador general intenta asignar o quitar el acceso de administrador general
- **THEN** el panel de administración no se lo permite
