# Spec Delta

## MODIFIED Requirements

### Requirement: Visibilidad de comunicados
El sistema SHALL mostrar a administrador, comité y conserje todos los comunicados del condominio, y al residente solo los generales y los dirigidos a los edificios donde vive, en la lista, el detalle y el panel de inicio. Un comunicado con fecha «Visible hasta» anterior a hoy SHALL salir de la lista principal y del panel de inicio, y SHALL seguir disponible en la lista de vencidos y en su detalle para quien puede verlo.

#### Scenario: Comunicado de otro edificio
- **WHEN** un residente del edificio A abre por URL directa un comunicado dirigido al edificio B
- **THEN** el sistema responde 404

#### Scenario: Comunicado vencido
- **WHEN** la fecha «Visible hasta» de un comunicado ya pasó
- **THEN** no aparece en la lista principal ni en el panel de inicio, aparece en «Ver vencidos» con la insignia «Vencido» y su detalle se sigue abriendo

#### Scenario: Comunicado sin fecha de vigencia
- **WHEN** un comunicado no tiene fecha «Visible hasta»
- **THEN** sigue en la lista principal indefinidamente

#### Scenario: Fecha de vigencia pasada al publicar
- **WHEN** el administrador publica un comunicado con una fecha «Visible hasta» anterior a hoy
- **THEN** el formulario rechaza la fecha

## ADDED Requirements

### Requirement: Confirmación de lectura
El sistema SHALL permitir que un residente al que va dirigido un comunicado lo marque como leído una sola vez, y SHALL mostrar al administrador cuántas de las unidades destinatarias con residentes activos confirmaron la lectura. El conteo MUST ser por unidad: una unidad cuenta como confirmada si cualquiera de sus residentes activos marcó el comunicado.

#### Scenario: El residente marca como leído
- **WHEN** un residente abre un comunicado dirigido a él y pulsa «Marcar como leído»
- **THEN** queda registrado y el detalle le muestra «Leíste este comunicado» en lugar del botón

#### Scenario: Conteo por unidad
- **WHEN** dos residentes de la misma unidad marcan el comunicado como leído
- **THEN** el administrador ve esa unidad una sola vez entre las que confirmaron

#### Scenario: Unidades que faltan
- **WHEN** el administrador abre el detalle de un comunicado
- **THEN** ve «Unidades que confirmaron la lectura: X de Y» y la lista de unidades que aún no lo hacen

#### Scenario: Acceso por rol
- **WHEN** un miembro del comité, un conserje o un residente de otro edificio intenta marcar como leído
- **THEN** el sistema responde 403 o 404, y solo el administrador ve el conteo de confirmaciones
