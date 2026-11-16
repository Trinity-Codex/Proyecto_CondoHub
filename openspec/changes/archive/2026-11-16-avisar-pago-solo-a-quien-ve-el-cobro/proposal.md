## Por qué

Tras el Issue #46, cada residente ve solo los cobros de su período de residencia. Pero `Pago.registrar` sigue avisando a todos los residentes activos de la unidad. Si el administrador paga una deuda anterior a la llegada de un residente, a esa persona le llega "Registramos tu pago" y el enlace responde 404. Maxi lo reportó en el grupo del equipo.

## Qué cambia

- `Pago.registrar` avisa solo a los residentes activos que ven el cobro, usando `cobros_visibles` de `apps/condominios/residencias.py`.
- Se agregan pruebas en `apps/pagos/tests.py`: no avisa a quien llegó después del período, y no avisa a quien ya fue dado de baja.

Issue: #46 (`Refs #46` en este PR, porque el de #46 ya está cerrado). MoSCoW: Must, porque corrige un 404 que ve un residente.

## Fuera de alcance

- Los avisos de emisión de cobros (`gastos/servicios.py`). Ese caso va aparte.
- Cambiar el texto o el canal del aviso.
- Cambiar la vista de pagos ni los permisos del administrador.
