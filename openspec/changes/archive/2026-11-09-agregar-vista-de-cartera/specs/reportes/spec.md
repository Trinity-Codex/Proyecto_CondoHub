## ADDED Requirements

### Requirement: Vista de cartera
El sistema SHALL mostrar al administrador general, para un mes, una fila por cada condominio activo que tiene asignado con el total emitido, el total recaudado, el porcentaje de recaudación, la deuda anterior y las unidades morosas, iguales a las del reporte de recaudación de ese condominio, más una fila de totales, un enlace al reporte de cada uno y la descarga en CSV segura. MUST NOT mostrar condominios no asignados ni nombres o RUT de residentes.

#### Scenario: Cifras iguales al reporte de cada condominio
- **WHEN** el administrador general abre la cartera de octubre y sus condominios asignados A y B tienen el período de octubre emitido
- **THEN** cada fila muestra el emitido, el recaudado, el % de recaudación, la deuda anterior y las unidades morosas del reporte de recaudación de ese período, con todos los edificios, y la fila de totales suma las filas y calcula su % como recaudado total por 100 dividido por emitido total

#### Scenario: Condominio sin período emitido en el mes
- **WHEN** uno de los condominios asignados no tiene emitido el período del mes elegido
- **THEN** su fila aparece con «Sin período emitido», sin cifras ni enlace, y no suma en los totales

#### Scenario: Mes por defecto y mes inválido
- **WHEN** se abre la cartera sin `?mes=`, o con un mes mal escrito o sin períodos emitidos en los condominios asignados
- **THEN** se muestra el mes más reciente que tiene un período emitido en alguno de ellos, sin error; si ninguno tiene períodos emitidos, la página lo indica

#### Scenario: Solo los condominios asignados
- **WHEN** el administrador general tiene asignados A y B, y existen además el condominio C y un condominio inactivo asignado
- **THEN** la página y el CSV muestran solo A y B

#### Scenario: Reporte de un condominio desde la cartera
- **WHEN** el administrador general abre el enlace de la fila de A
- **THEN** ve el reporte de recaudación de A para ese período, en modo consulta y con las mismas cifras de la fila, sin cambiar su condominio activo; si pide por URL el reporte o el CSV de C, recibe 404

#### Scenario: Sin datos personales
- **WHEN** el administrador general abre la cartera, el reporte de un condominio desde ella o sus descargas CSV
- **THEN** no aparece ningún nombre ni RUT de residente

#### Scenario: Descarga en CSV segura
- **WHEN** el administrador general descarga la cartera en CSV y un condominio asignado se llama «=SUMA(1)»
- **THEN** el archivo trae una fila por condominio y la de totales, y el nombre queda escrito como texto, sin que Excel lo evalúe

#### Scenario: Superusuario
- **WHEN** el superusuario abre la cartera
- **THEN** ve todos los condominios activos, como en el resto del sitio

#### Scenario: Acceso por rol
- **WHEN** un administrador, un miembro del comité, un conserje o un residente sin acceso de administrador general abre la cartera, su CSV o el reporte de un condominio desde ella
- **THEN** el sistema responde 403, y una persona sin sesión es llevada al inicio de sesión
