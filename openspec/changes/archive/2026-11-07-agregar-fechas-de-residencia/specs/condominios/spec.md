# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
