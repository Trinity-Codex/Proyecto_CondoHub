# Tasks

## 1. Cálculo (apps/gastos/evolucion.py)

- [x] 1.1 Serie mensual del condominio (apertura, aportes, egresos, ajustes, cierre, emitido) con validación de cobertura; verificar con pruebas que cada cierre es igual a `saldo_fondo(condominio, periodo)` y que apertura + movimientos = cierre.
- [x] 1.2 Geometría del gráfico SVG a partir de la misma serie, con soporte de saldos negativos; verificar con una prueba que los valores de las barras son los de la tabla.
- [x] 1.3 Aportes por edificio mes a mes y saldo por edificio con `repartir`; verificar con una prueba que los saldos suman el saldo total y que los ítems de cobro no cuentan.
- [x] 1.4 Aporte acumulado por unidad y por residente según fechas de residencia; verificar con pruebas de residencia que empieza o termina a mitad del historial.

## 2. Vistas y plantillas

- [x] 2.1 Vista de evolución (administrador y comité) con gráfico, tabla, edificios, unidades y residentes; verificar 200 para ambos y 403 para residente y conserje.
- [x] 2.2 Desglose mensual de una unidad; verificar 200 para administrador, comité y residente de la unidad, 403 para otro residente y conserje, 404 para una unidad de otro condominio.
- [x] 2.3 Vista «Mi aporte al fondo» del residente (saldo total y solo sus unidades, con `cobros_visibles`); verificar que no muestra otras unidades.
- [x] 2.4 Enlaces desde el fondo y en el menú del residente; verificar a 1440×900 y 375×812.

## 3. Demo y pruebas

- [x] 3.1 Tres meses emitidos y pagados adicionales en `apps/gastos/demo.py`; actualizar la huella de `apps/core` y verificar con `python manage.py cargar_demo --reiniciar`.
- [x] 3.2 Pruebas de cuadre, roles y aislamiento entre condominios en `apps/gastos/tests_evolucion.py`; `python manage.py test apps` completo y `openspec validate --all --strict`.

## Workflow follow-up

- `/code-review high` antes de abrir el PR.
- Archivar el cambio en el mismo PR, antes de unirlo.
