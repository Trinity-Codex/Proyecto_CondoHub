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

### Requirement: Importación desde planilla
El sistema SHALL permitir que el administrador importe al condominio activo edificios, unidades y residentes desde un archivo CSV, con una vista previa de los errores por fila antes de confirmar. La importación MUST ser todo o nada y reimportar el mismo archivo MUST NOT duplicar datos.

#### Scenario: Vista previa sin errores
- **WHEN** el administrador sube un CSV válido
- **THEN** el sistema muestra cuántos edificios, unidades, cuentas y residentes se crearán o actualizarán, sin guardar nada todavía

#### Scenario: Errores por fila
- **WHEN** el archivo tiene una fila con RUT inválido, un correo repetido con otros datos, una unidad repetida o una alícuota o fecha inválida
- **THEN** la vista previa muestra el número de fila y el error, y no permite confirmar

#### Scenario: Alícuotas que no suman 1
- **WHEN** las alícuotas del condominio, con las del archivo, no suman 1
- **THEN** la vista previa lo indica como error y no permite confirmar

#### Scenario: Todo o nada
- **WHEN** falla el guardado de una fila al confirmar
- **THEN** no queda guardada ninguna fila del archivo

#### Scenario: Reimportar el mismo archivo
- **WHEN** el administrador importa dos veces el mismo archivo
- **THEN** el condominio queda con los mismos edificios, unidades, cuentas y residentes que después de la primera vez

#### Scenario: Cuentas nuevas e invitaciones
- **WHEN** el archivo trae el correo de una persona sin cuenta y el administrador confirma con «Enviar invitaciones»
- **THEN** se crea la cuenta, queda como residente con su fecha de inicio y recibe el correo para definir su contraseña; sin esa opción, no se envía ningún correo

#### Scenario: Plantilla de ejemplo
- **WHEN** el administrador descarga la plantilla
- **THEN** recibe un CSV con los encabezados y filas de ejemplo que la misma importación acepta

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente intenta importar o descargar la plantilla
- **THEN** el sistema responde 403

### Requirement: Filtro de unidades por ocupación
El sistema SHALL filtrar el listado de unidades con `?ocupacion=con_residentes|sin_residentes` (con residentes activos, el mismo criterio de «Con residencia vigente» del panel de inicio) y mostrar chips con la cantidad de unidades de cada grupo, contadas sobre las unidades del condominio activo. El orden (edificio, piso, número) se mantiene. Solo administrador y comité pueden abrirlo.

#### Scenario: Unidades sin residentes
- **WHEN** el administrador abre `?ocupacion=sin_residentes`
- **THEN** cada edificio muestra solo sus unidades sin residentes activos y los chips cuentan ambos grupos

#### Scenario: Cuadra con el panel
- **WHEN** se suman las unidades «Con residentes» de los chips
- **THEN** el resultado coincide con las unidades que tienen algún residente activo y el panel cuenta los mismos residentes

#### Scenario: Aislamiento y acceso
- **WHEN** otro condominio tiene unidades, o un conserje o residente abre el listado
- **THEN** ninguna cantidad incluye lo ajeno y el conserje y el residente reciben 403

### Requirement: Búsqueda de unidades y residentes
El sistema SHALL filtrar el listado de unidades con `?q=` por número de unidad y por nombre o apellido de sus residentes activos, sin distinguir mayúsculas ni tildes; si el texto tiene varias palabras, cada una MUST coincidir. Solo para el administrador SHALL buscar también por el inicio del RUT, con o sin puntos y guion. La búsqueda MUST combinarse con `?ocupacion=` y solo administrador y comité pueden usarla.

#### Scenario: Buscar por número de unidad
- **WHEN** el administrador abre Unidades con `?q=504`
- **THEN** cada edificio muestra solo sus unidades cuyo número contiene «504»

#### Scenario: Buscar por nombre sin tildes
- **WHEN** el comité busca «perez ana» y la residente activa ficticia «Ana Pérez» vive en la unidad 101
- **THEN** el listado muestra la unidad 101 con sus residentes activos

#### Scenario: Buscar por RUT con o sin puntos
- **WHEN** el administrador busca «12.345.678-5», «123456785» o «12345»
- **THEN** en los tres casos aparece la unidad del residente activo con RUT `12345678-5`

#### Scenario: El comité no busca por RUT
- **WHEN** un miembro del comité busca «12.345.678-5» o «12345», que solo coinciden con el RUT de un residente
- **THEN** el listado no muestra esa unidad, de modo que la búsqueda no permite deducir un RUT

#### Scenario: Residente dado de baja
- **WHEN** el administrador busca el nombre de una persona cuya residencia está dada de baja
- **THEN** su antigua unidad no aparece por ese nombre

#### Scenario: Búsqueda con chips
- **WHEN** el administrador abre `?q=Torres&ocupacion=con_residentes`
- **THEN** ve solo las unidades con residentes que coinciden con «Torres», los chips cuentan las unidades del resultado de la búsqueda y «Limpiar filtros» quita `q` y `ocupacion`

#### Scenario: Búsqueda vacía
- **WHEN** se abre Unidades con `?q=` vacío o solo con espacios
- **THEN** se muestra el listado completo y no aparece «Limpiar filtros»

#### Scenario: Aislamiento y acceso
- **WHEN** otro condominio tiene una unidad «504» con la residente ficticia «Ana Pérez», o un conserje o residente abre `?q=504`
- **THEN** el administrador no ve nada del otro condominio y el conserje y el residente reciben 403

### Requirement: Sugerencias de búsqueda de unidades
El sistema SHALL responder en JSON, solo por GET, hasta 10 unidades del condominio activo que coinciden con `q` bajo las mismas reglas del listado, cada una con su edificio, número y residentes activos, y el RUT con puntos solo para el administrador. Con menos de 2 caracteres MUST devolver una lista vacía. La respuesta MUST pedir que no se guarde en caché y MUST NOT incluir más campos de los que el listado muestra a ese rol.

#### Scenario: Sugerencias del administrador
- **WHEN** el administrador pide sugerencias para «Pér» y la residente ficticia «Ana Pérez», RUT `12345678-5`, vive en la unidad 101 de la Torre A
- **THEN** recibe la unidad 101 de la Torre A con «Ana Pérez» y «12.345.678-5», y la cabecera `Cache-Control` incluye `no-store`

#### Scenario: Sugerencias del comité
- **WHEN** un miembro del comité pide sugerencias para «Pér»
- **THEN** recibe la misma unidad con el nombre y sin ningún RUT

#### Scenario: Menos de 2 caracteres
- **WHEN** alguien con acceso pide sugerencias para «P» o para un texto vacío
- **THEN** recibe una lista vacía sin consultar las unidades

#### Scenario: Más de 10 coincidencias
- **WHEN** el condominio tiene 15 unidades cuyo número contiene «10»
- **THEN** la respuesta trae 10 unidades en el orden del listado e indica que hay más

#### Scenario: Aislamiento
- **WHEN** el administrador del condominio A pide sugerencias para un nombre que solo existe en el condominio B
- **THEN** recibe 0 resultados

#### Scenario: Acceso por rol
- **WHEN** un conserje o un residente pide sugerencias, o alguien las pide por POST
- **THEN** el conserje y el residente reciben 403, el POST recibe 405 y una persona sin sesión es llevada al inicio de sesión
