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
El sistema SHALL vincular personas a unidades como propietario, arrendatario o familiar/otro ocupante, con una fecha de inicio obligatoria que no puede ser futura; MUST impedir que una persona sea residente activa dos veces de la misma unidad; y SHALL permitir que el administrador dé de baja a un residente sin borrar el registro, guardando la fecha de término.

#### Scenario: Agregar un residente sin cuenta
- **WHEN** el administrador agrega como residente un correo que no tiene cuenta
- **THEN** el sistema indica que primero hay que crear la cuenta

#### Scenario: Fecha de inicio futura
- **WHEN** el administrador agrega un residente con una fecha de inicio futura
- **THEN** el formulario rechaza la fecha y no crea el residente

#### Scenario: Dar de baja a un residente
- **WHEN** el administrador da de baja a un residente
- **THEN** el registro se conserva inactivo con la fecha de término de ese día, y si la persona no vive en otra unidad del condominio pierde allí el rol residente

#### Scenario: Reasignar a un residente dado de baja
- **WHEN** el administrador vuelve a asignar a la misma unidad a una persona dada de baja, con una nueva fecha de inicio
- **THEN** el registro queda activo con la nueva fecha de inicio y sin fecha de término

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente intenta asignar o dar de baja a un residente
- **THEN** el sistema responde 403

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

### Requirement: Eliminación protegida de edificios y unidades
El sistema MUST impedir eliminar un edificio con unidades o comunicados dirigidos a él, y una unidad con residentes activos, reservas o cobros de gastos comunes, explicando el motivo.

#### Scenario: Unidad con cobros
- **WHEN** el administrador intenta eliminar una unidad que tiene cobros de gastos comunes
- **THEN** el sistema explica el motivo y no la elimina

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité intenta eliminar un edificio o una unidad
- **THEN** el sistema responde 403

### Requirement: Aviso de alícuotas descuadradas
El sistema SHALL avisar al administrador cuando, después de crear, editar o eliminar una unidad, las alícuotas del condominio no suman 1.

#### Scenario: Alícuotas que no suman 1
- **WHEN** el administrador crea una unidad y las alícuotas del condominio dejan de sumar 1
- **THEN** la unidad se guarda y el sistema muestra una advertencia con la suma actual

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité intenta crear o editar una unidad
- **THEN** el sistema responde 403 y no se muestra ningún aviso
