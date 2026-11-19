## ADDED Requirements

### Requirement: Proyección anual de gastos comunes
El sistema SHALL proyectar los gastos comunes del año siguiente desde los egresos emitidos del año base, reajustados por IPC y crecimiento. La proyección MUST mostrarse por mes y por unidad en pesos enteros, con el prorrateo y el fondo de reserva vigentes, sus supuestos y parámetros en la URL. Solo el administrador y el comité acceden, en modo de solo lectura.

#### Scenario: Proyección reproducible con sus supuestos
- **WHEN** el administrador abre la proyección dos veces con el mismo año base, IPC y crecimiento, sin cambios en los datos
- **THEN** ambas muestran los mismos montos y el cuadro de supuestos indica año base, año proyectado, IPC, crecimiento, criterio de prorrateo, porcentaje del fondo, y meses reales y estimados

#### Scenario: Meses sin período emitido
- **WHEN** el año base tiene algunos meses sin período emitido
- **THEN** esos meses se proyectan desde el promedio de los meses reales y la pantalla los marca como estimados

#### Scenario: Sin meses reales
- **WHEN** el año base no tiene ningún período emitido
- **THEN** la pantalla lo indica y no muestra una proyección inventada

#### Scenario: Total de cada mes cuadra con las unidades
- **WHEN** se proyecta un mes cuyo monto no se reparte en partes enteras exactas entre las unidades
- **THEN** la suma de lo proyectado por unidad es igual al total proyectado del mes, sin pesos de más ni de menos

#### Scenario: Cambio proporcional de los parámetros
- **WHEN** un mes base tiene $100.000 de egresos y se proyecta con IPC 10 % y crecimiento 0 %, y luego con IPC 10 % y crecimiento 10 %
- **THEN** los egresos proyectados del mes son $110.000 y $121.000, respectivamente

#### Scenario: Parámetros inválidos
- **WHEN** el usuario ingresa en la URL un IPC o crecimiento que no es número o está fuera del rango permitido
- **THEN** la pantalla muestra el error del formulario sin proyección y sin error del servidor, y el CSV no se descarga

#### Scenario: CSV igual a la pantalla
- **WHEN** el administrador o el comité descarga el CSV de la proyección con los mismos parámetros
- **THEN** el archivo contiene los mismos montos por mes y por unidad, y los mismos supuestos que la pantalla

#### Scenario: Ítems de cobro fuera de la base
- **WHEN** un período emitido del año base tiene ítems de cobro
- **THEN** la base de ese mes son solo sus egresos, sin los ítems

#### Scenario: Acceso por rol
- **WHEN** un administrador o un miembro del comité abre la proyección o su CSV
- **THEN** la ve con los datos de su condominio, y un residente o conserje recibe 403

#### Scenario: Aislamiento entre condominios
- **WHEN** otro condominio tiene períodos emitidos y unidades
- **THEN** la proyección no usa sus egresos ni lista sus unidades
