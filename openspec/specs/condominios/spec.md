# condominios Specification

## Purpose
Modelar la cartera multi-condominio: condominios, edificios, unidades con alícuota, residentes y roles por
condominio, y aislar los datos de cada condominio (RF01, RF15, RF16, RNF02). Código: `apps/condominios`, `apps/core`.

## Requirements

### Requirement: Estructura del condominio
El sistema SHALL organizar cada condominio en edificios y unidades, con número, piso, tipo (departamento, casa, local, estacionamiento o bodega) y alícuota decimal, administrables desde el sitio por el administrador.

#### Scenario: Edificio duplicado
- **WHEN** el administrador crea un edificio con un nombre que ya existe en el condominio
- **THEN** el formulario rechaza el nombre repetido

### Requirement: Residentes de una unidad
El sistema SHALL vincular personas a unidades como propietario o arrendatario, y MUST impedir que una persona sea residente activa dos veces de la misma unidad.

#### Scenario: Agregar un residente sin cuenta
- **WHEN** el administrador agrega como residente un correo que no tiene cuenta
- **THEN** el sistema indica que primero hay que crear la cuenta

### Requirement: Roles por condominio
El sistema SHALL asignar los roles administrador, comité, conserje y residente por condominio (membresía), de modo que una persona pueda tener roles distintos en condominios distintos. El superusuario actúa como administrador en todos.

#### Scenario: Conserje sin datos financieros
- **WHEN** un conserje intenta abrir la cobranza o los gastos comunes
- **THEN** el sistema responde 403

### Requirement: Condominio activo y aislamiento
El sistema SHALL mostrar en cada página solo los datos del condominio activo de la sesión, permitir cambiarlo desde el menú a quien tenga acceso a varios, y MUST responder 404 al pedir un registro de otro condominio o de otra persona.

#### Scenario: Registro de otro condominio
- **WHEN** un usuario abre por URL directa un registro de un condominio donde no tiene rol
- **THEN** el sistema responde 404 sin revelar que el registro existe
