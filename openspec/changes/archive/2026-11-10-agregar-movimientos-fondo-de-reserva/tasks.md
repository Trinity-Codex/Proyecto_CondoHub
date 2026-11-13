# Tasks

Implementación autorizada por Walther el 10 de noviembre de 2026. Históricos, corte y apertura aprobados según `design.md`; specs y pruebas conservan cobertura explícita para #55.

## 1. Modelo, apertura y operaciones manuales

- [x] 1.1 Registrar la revisión de las tres decisiones de `design.md` antes de aplicar; verificar que specs y tareas reflejen la resolución, incluido el manejo de cobertura para #55.
- [x] 1.2 Crear `MovimientoFondo` y una sola migración nueva de `gastos`, sin ingresos retroactivos; comprobar en MySQL unicidad del inicial y del ingreso, signos por tipo y relaciones válidas. No editar migraciones unidas ni otras apps.
- [x] 1.3 Implementar inicial, egreso y ajuste en `apps/gastos/fondo.py`, con validaciones compartidas, bloqueo del condominio y `registrar` en la misma transacción; pruebas directas de servicio en `apps/gastos/tests.py` rechazan proveedor/período ajeno y campos manipulados.
- [x] 1.4 Probar «Administrador configura el saldo inicial» y «Saldo inicial repetido» por separado en `apps/gastos/tests.py`; verificar movimiento único, autor y auditoría, incluyendo monto cero, monto negativo rechazado y dos intentos concurrentes.
- [x] 1.5 Probar «Administrador registra un egreso autorizado» y «Egreso inválido» por separado; parametrizar cada dato inválido, monto cero/negativo, proveedor ajeno e importe sobre `MONTO_MAXIMO`. Verificar persistencia, signo, autor y ausencia de cambios ante error.
- [x] 1.6 Probar «Ajuste trazable»: corrección positiva/negativa, rechazo de cero o falta de respaldo, y conservación del movimiento anterior; comprobar que no hay rutas ni permisos Admin para editar o borrar movimientos.
- [x] 1.7 Probar «Fallo de auditoría de un movimiento manual» para inicial, egreso y ajuste, forzando error en C1 y verificando rollback de movimiento y saldo.
- [x] 1.8 Probar «Movimiento manual anterior a la apertura» y «Saldo contable negativo» por separado; verificar rechazo sin efectos para fecha fuera de cobertura y aceptación auditada del saldo negativo documentado.

## 2. Consultas públicas C5 y legado

- [x] 2.1 Implementar las firmas exactas `saldo_fondo(condominio, hasta_periodo=None)` y `movimientos_fondo(condominio, periodo=None)` en `apps/gastos/fondo.py`; documentar tipos, corte, errores y ejemplo en sus docstrings y comprobar que las llamadas descritas en `design.md` funcionan.
- [x] 2.2 Probar «Saldo igual a movimientos y aportes cobrados»: comparar `int`, suma algebraica y suma de `monto_fondo_reserva` persistidos para cada nueva emisión, incluyendo redondeo y otro condominio.
- [x] 2.3 Probar «Corte mensual inclusivo para C5»: ingreso emitido al mes siguiente, egresos en el último y primer día del siguiente mes, febrero bisiesto, diciembre/enero y período abierto; comprobar también que `None` suma todo el libro.
- [x] 2.4 Probar «Movimientos mensuales para C5»: límites inclusivos, orden `fecha, pk`, campos y relaciones disponibles, consulta sin período y exclusión de movimientos ajenos.
- [x] 2.5 Probar «Período ajeno en C5» para ambas funciones; verificar `ValidationError` sin devolver datos del otro condominio.
- [x] 2.6 Probar «Fondo sin movimientos» en un condominio sin legado: entero cero y queryset vacío, sin consultas que creen datos.
- [x] 2.7 Probar «Históricos anteriores a la activación» en `apps/gastos/tests.py`: base con emitidos previos conserva cobros, no recibe ingresos de migración, exige apertura documentada, evita doble conteo y da códigos `fondo_sin_apertura`/`fondo_sin_cobertura` en ambas consultas. Verificar fecha inicial después del último legado y apertura opcional sin legado, nunca posterior al primer movimiento existente.

## 3. Integración con emisión y auditoría

- [x] 3.1 Ampliar `emitir_periodo(periodo, *, usuario=None)`, sumar aportes guardados y crear ingreso único con fecha de fin del mes; pasar usuario desde la vista. Registrar emisión e ingreso con acciones C1 existentes en la misma transacción, sin modificar auditoría. Verificar compatibilidad de demo y callers actuales de gastos, pagos y notificaciones.
- [x] 3.2 Conservar y ejecutar las pruebas «Emisión bloqueada por alícuotas» y «Emisión sin egresos» de `tests_emision.py`; ampliar aserciones en `tests.py` para confirmar que tampoco quedan ingreso ni eventos.
- [x] 3.3 Probar «Doble clic al emitir» en MySQL con dos transacciones reales: un juego de cobros, un ingreso, un evento de emisión y un evento de creación del ingreso; verificar también reintento secuencial y orden de bloqueos condominio/período.
- [x] 3.4 Probar «Administrador emite e ingresa el aporte exacto»: usuario real y sumas con redondeo; comprobar C1 con estado antes/después, monto y condominio. Añadir caso de llamada sin usuario que queda como Sistema.
- [x] 3.5 Probar «Emisión atómica» con errores de ingreso, C1 y notificación persistida; verificar período abierto y ausencia de cobros, movimientos, notificaciones y eventos parciales.
- [x] 3.6 Probar «Aporte redondeado a cero» y «Emisión anterior a la apertura» por separado: ingreso único de cero en emisión válida y rechazo sin efectos cuando el período queda fuera de cobertura.

## 4. Pantalla y acceso por rol

- [x] 4.1 Agregar formularios, vistas, rutas y plantillas del fondo en `apps/gastos`, enlazadas desde períodos; usar `RolRequeridoMixin`, `CondominioQuerysetMixin`, `MontoField`, C6, `pesos` e insignias con texto. Verificar saldo contable, detalle, paginación y aviso de apertura; no mostrar residentes/unidades (#46 no aplica). Sin filtros nuevos; si se añaden, usar `FiltrosGetMixin`.
- [x] 4.2 Probar «Comité solo consulta»: listado/detalle disponibles y GET/POST de todos los formularios manuales en 403, sin cambios. Verificar también formularios y POST válidos del administrador, incluidos inicial y ajuste.
- [x] 4.3 Probar «Conserje y residente sin acceso al fondo» por rol y endpoint, tanto GET como POST; comprobar 403 y ausencia de filtración o cambios.
- [x] 4.4 Probar «Movimiento de otro condominio» con administrador y comité: detalle ajeno 404 y ausencia en listado; verificar rechazo de proveedor ajeno enviado a mano y condominio/autor asignados por servidor.
- [x] 4.5 Probar «Comité consulta pero no emite», «Conserje y residente sin acceso a la emisión» y «Período de otro condominio al emitir» por separado: consulta permitida según rol, GET/POST 403 o 404 y ningún cobro, ingreso o evento creado.

## 5. Demo y comprobaciones integradas

- [x] 5.1 Agregar a `apps/gastos/demo.py` inicial ficticio, ingresos mediante las emisiones actuales y egreso ficticio con proveedor y acuerdo; ampliar `huella_demo`/`HUELLA` en `apps/core/tests.py`. Comprobar carga, recarga y reinicio solo en base de pruebas con `CargarDemoTest`, preservando claves consumidas por otras apps. Probar que `RESTRICT` impide borrar un período cuyos movimientos se conservan y permite eliminar el condominio completo con sus movimientos en cascada, sin romper el reinicio de la demo. No ejecutar `cargar_demo --reiniciar` en desarrollo.
- [x] 5.2 Ejecutar `venv\Scripts\python.exe manage.py makemigrations --check` y `venv\Scripts\python.exe manage.py test apps` completo; guardar resultados sin errores, incluida concurrencia en MySQL y regresiones de pagos/notificaciones/cartera.
- [x] 5.3 Levantar la aplicación en puerto **8008** y hacer verificación visual con medición del DOM a **375 y 1440 px**: saldo, tabla/listado, detalle, apertura, egreso y ajuste. Registrar anchos de viewport/documento, ausencia de desbordamiento de página, etiquetas/errores asociados y controles utilizables; cerrar el servidor al terminar.
- [x] 5.4 Ejecutar `openspec validate agregar-movimientos-fondo-de-reserva --strict`, `openspec validate --all --strict` y `codex review --base main` antes de dejar el PR listo; resolver hallazgos, verificar diff solo del alcance y esperar CI `pruebas` verde.

## Workflow follow-up

- Propuesta revisada e implementación autorizada el 10 de noviembre de 2026; mantener borrador hasta completar controles.
- Antes de archivar, actualizar contra `main` y repetir controles del proyecto; archivar el cambio y sincronizar `gastos-comunes` en este mismo PR.
- La unión la decide Walther en ese momento. No unir, mencionar usuarios ni enviar mensajes al equipo desde esta tarea.

## Evidencia de implementación

- Suite MySQL: 749 pruebas OK (96,559 s); incluye dos conexiones reales para apertura y emisión, rollback, migración sin ingresos retroactivos y reinicio demo en pruebas.
- SQLite: 153 pruebas de gastos OK, con tres de bloqueo omitidas por falta de SELECT FOR UPDATE.
- makemigrations --check sin cambios; OpenSpec estricto del cambio válido y global 13/13.
- Revisión codex review --base main completada por lectura: P2 de SQLite reproducido y corregido con skipUnlessDBFeature. El ejecutor de revisión no pudo ejecutar Python/OpenSpec; la sesión implementadora ejecutó los controles.
- Casos de borde de validación reproducidos y corregidos con pruebas: respaldo nulo y fecha normalizada.
- Visual: 14 capturas y medidas DOM a 375/1440, cinco pantallas más errores y aviso de apertura. Sin desbordamiento de página; etiquetas y errores asociados. Puerto 8008 cerrado, base de pruebas eliminada y desarrollo intacto.
- CI del commit de implementación 2d9e437: pruebas verde, ejecución 42829110535. Tras archivo y actualización con origin/main se repiten controles y CI.
