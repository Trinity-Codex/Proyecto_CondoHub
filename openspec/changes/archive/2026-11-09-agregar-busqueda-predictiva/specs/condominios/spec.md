## ADDED Requirements

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
