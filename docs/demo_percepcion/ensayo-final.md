# Acta de preparación y ensayo final · #101

**Estado: preparación documental; ensayo integrado PENDIENTE.** Corte de consulta: 16-nov-2026, 14:22, America/Santiago. Walther confirmó que la presentación sigue pendiente. No se acredita ensayo del domingo 15 ni congelamiento a las 17:00 de ese día. Los plazos originales del plan son antecedentes, no hechos cumplidos.

Guion, operación y pauta: [DEMO_PERCEPCION_16NOV.md](../equipo/DEMO_PERCEPCION_16NOV.md). Fuente de alcance: [Issue #101 con plan maestro](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/101) y [milestone demo_percepcion](https://github.com/Trinity-Codex/Proyecto_CondoHub/milestone/3).

## Snapshot comprobado

- Main remoto y base local: `6eaa59e2acd48847d8348359ed32a008a310814e`, con #93 integrado por [PR #102](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/102). `git fetch origin main`, cambio a main y `git pull --ff-only origin main`: ya actualizado.
- CI del **SHA de main**: `pruebas`, `completed / success`, [ejecución 43652925831](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43652925831). Verificado mediante la API de check-runs, no inferido del CI de otro PR.
- Rama documental: `codex/101-guion-ensayo-demo`, creada desde ese main. No incorpora #94 ni ramas de colaboradores. Su SHA/PR y CI se registran en la entrega del PR; no son un snapshot integrado de todas las entregas.
- SHA final para presentación: **PENDIENTE**. Cualquier cambio posterior de main exige actualizar esta matriz y contrastar nuevamente la evidencia.

## Matriz de las ocho dependencias

Los SHA siguientes son los heads de los PR, salvo donde se indica el squash integrado. «CI verde» describe ese commit; no demuestra que los PR funcionen combinados. Los estados se consultaron en GitHub el 16-nov; no se editaron Issues ni se marcaron casillas allí.

| Issue / responsable | PR y SHA comprobados | Estado al corte | Evidencia disponible y límite |
|---|---|---|---|
| [#93](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/93) · Walther | [#102](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/102), head `1613b26b91faa3246f03adf6ded15be7ed2d450c`; squash/main `6eaa59e2acd48847d8348359ed32a008a310814e` | Issue cerrado; PR unido 14-nov; CI verde en PR y main | Configuración/comando aislados y datos financieros en main; [operación](../DEMO_CLIENTE_LOCAL.md). No sustituye los loaders de #96/#98. |
| [#94](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/94) · Walther | [#106](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/106), `1499682113e7ce97375c28bb8fa7c8933c433245` | Abierto, listo; CI verde; **sin unir** | Nota local `.codex/orquestador/notas/n94-impl.md`: 755 pruebas locales (una omitida Windows), CI 755 OK; capturas/mediciones de su rama. No acredita el conjunto #101. |
| [#95](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/95) · Maximiliano | Sin PR relacionado identificado en búsquedas/listados revisados; SHA PENDIENTE | Issue abierto | Pulido de acceso, comunidad, panel y reservas; evidencia PENDIENTE. No se atribuye como entregado. |
| [#96](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/96) · Maximiliano | Sin PR relacionado identificado; SHA PENDIENTE | Issue abierto | Reservas posteriores al 16, comunicados vigentes/vencidos y lectura; evidencia PENDIENTE. |
| [#97](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/97) · Winderson | [#104](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/104), `ca53f42b622a7e21ceff10d67fe7a98787801fd1` | Abierto, listo; CI verde; **sin unir** | Pulido de pagos/proveedores/incidentes. El QA #100 informa correcciones móviles de esta rama; falta verificar con el conjunto integrado. |
| [#98](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/98) · Winderson | [#103](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/103), `aff64368d8d3834144772eb99d538eeb6874c166` | Abierto, listo; CI verde; **sin unir** | PR declara pagos de Los Aromos, proveedores y estado resuelto; no existen por ello automáticamente en la base local anterior. Incluye cambio en prueba compartida, descrito abajo. |
| [#99](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/99) · Maximiliano | Sin PR relacionado identificado; SHA PENDIENTE | Issue abierto | Informe de comunidad/residente y evidencia por rol/resolución PENDIENTES. |
| [#100](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/100) · Winderson | [#105](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/105), `83c35d60595cf90e64f08e66198f1e1f1e610eda` | Abierto, listo; CI verde; **sin unir** | [Informe en su SHA](https://github.com/Trinity-Codex/Proyecto_CondoHub/blob/83c35d60595cf90e64f08e66198f1e1f1e610eda/docs/demo_percepcion/qa-operacion-finanzas.md): revisión local main + #97 + #98, GET por roles y 375/1440. No es evidencia de main ni de equipo/conexión de presentación. |

CI de los heads abiertos: [#103](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43861479468), [#104](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43862581462), [#105](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43862688393), [#106](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43915407663). Todos `pruebas / SUCCESS` al consultar.

### Revisión del punto compartido de PR #103

Leído el diff remoto de `apps/core/tests_demo_cliente.py`, sin traer la rama ni editarla. Agrega `huella_modo_cliente()` desde una copia de la huella normal y suma los deltas de pagos, proveedores, incidente y notificaciones de #98; sustituye la igualdad con la huella normal solo en la prueba del modo cliente. Las comprobaciones del fondo siguen en el método. Es una lectura del alcance, **no autorización de unión ni validación completa del conjunto**. Walther debe revisar ese cambio compartido antes de decidir integración; los futuros datos de #96 también deberán conciliarse sin debilitar la huella normal.

## Comprobación local de preparación

Lecturas de configuración, comando, cargadores, rutas, permisos, specs y documentación; no se ejecutó el comando de preparación ni se levantó un servidor en #101.

La SQLite existente es `.demo_cliente/demo.sqlite3` dentro del repositorio de Desktop. Consulta directa con `sqlite3.connect(...?mode=ro, uri=True)`, sin sesión Django ni escrituras: períodos Vista Verde 09/2026 EMITIDO, 10/2026 EMITIDO, 11/2026 ABIERTO; Los Aromos 10/2026 EMITIDO. La consulta acotada no valida usuarios, todos los datos, roles ni renderizado.

Saldos de referencia de #93: Vista Verde $1.140.537 y Los Aromos $533.925, contables, no caja. Deben coincidir con movimientos en la foto final. El QA de #100 declara Los Aromos recaudado $416.213 **en su combinación de ramas**; no usar esa cifra para describir main. La validación de saldos y actividad completa del snapshot final queda PENDIENTE.

No repetir la preparación para fingir nuevos ejemplos: si hay condominios demo existentes, el cargador retorna antes de ejecutar las apps. La vía segura pendiente consiste en conservar esa base y definir/verificar una configuración temporal que use una SQLite nueva dentro de `.demo_cliente/`, tanto para preparar como para servir. No se borró, reinició ni sustituyó ninguna base. Ver detalle y comandos actuales en el guion.

Evidencia anterior disponible localmente para #94: `.demo_cliente/n94/evidencia/`, ignorada; su nota registra 52 JPG, 46 mediciones y foco. Corresponde al SHA de PR #106 y a sus rutas/roles registrados. No son capturas integradas de #101 ni respaldo validado de la presentación final.

## Bloqueos, responsables y siguiente acción

| Bloqueo / límite | Responsable | Siguiente acción necesaria |
|---|---|---|
| #94/#97/#98/#100 sin integrar | Autores; Walther decide uniones | Revisar heads y evidencia, actualizar con main y obtener autorización expresa antes de cualquier merge. Esta fase no une nada. |
| #95/#96/#99 sin entrega comprobada | Maximiliano | Entregar PR/SHA/evidencia de su bloque; comprobarlos antes del ensayo. No cambiar su dueño/plazo desde #101. |
| SQLite actual no incorpora futuros loaders por repetición | Walther, con inventarios de ambos colaboradores | Definir y verificar preparación no destructiva en una ruta nueva; mantener base actual. Contrastar fechas, saldos, actividad y aislamiento. |
| Falta combinación probada y CI final | Walther | Tras integraciones autorizadas, identificar SHA final, comprobar CI y controles MySQL/OpenSpec. |
| Ensayo conjunto, equipo y conexión sin comprobar | Los tres; Walther coordina | Acordar hora real, equipo y conexión; recorrer y registrar resultados/capturas antes de presentar. No sustituirlo por QA individual. |

Auditoría/Rendición continúan con pantalla provisional; PDF/comprobante y anulación no están disponibles como entrega integrada. PR #73 y #74 abiertos **en borrador** al consultar. PWA tiene manifest/íconos; sin conexión sigue pendiente (#26). No iniciar #29/#50 ni cerrar #59 por esta preparación.

## Pauta de ensayo por ejecutar

Esta tabla es un plan de comprobación, no resultados observados. Usar solo datos ficticios y los enlaces de las listas para objetos de esa base. Registrar por cada ruta: cuenta/rol, condominio, URL exacta, HTTP esperado/observado, importes/fecha si aplican, resolución, captura y hallazgo. No introducir escrituras financieras para sostener el guion.

| Rol | Recorrido mínimo / restricción que contrastar | Resultado hoy |
|---|---|---|
| Administrador, ambos condominios | Inicio, unidades, comunicados, períodos, reporte, fondo, cobranza, cuenta de unidad, formulario de pago sin envío, proveedores e incidentes. Objetos ajenos: 404 donde corresponda. | PENDIENTE integrado |
| Comité | Consulta de períodos/reporte/fondo/cobranza/proveedores; formularios administrativos de pago/fondo: 403. Su rol adicional de residente no sustituye la prueba de residente puro. | PENDIENTE integrado |
| Residente Vista Verde y Los Aromos | Inicio, Mi cuenta y detalle propio, comunicados visibles, espacios/reservas e incidentes. Cobro ajeno: 404; administración financiera: 403. | PENDIENTE integrado |
| Conserje | Inicio/operación permitida; sin tarjetas de unidades/dinero, sin cobranza/reporte/fondo. | PENDIENTE integrado |
| Gerencia | Cartera de octubre y reportes de ambos asignados; sin nombres/RUT de residentes, sin cambiar condominio activo. Sin membresía comunitaria: no atribuirle permisos administrativos. | PENDIENTE integrado |
| Sin sesión | Acceso público de privacidad y redirección al login para rutas protegidas. | PENDIENTE integrado |

En **1440x900 y 375x812** medir `document.documentElement.scrollWidth <= innerWidth`, revisar tablas con desplazamiento interno, foco por teclado, etiquetas, ayudas y errores. No declarar errores de formulario comprobados si solo se abrió por GET. Registrar 403/404 esperados como control correcto; cualquier 500, enlace roto, dato real, diferencia monetaria o desborde de página es un bloqueo que requiere corregir o retirar de forma transparente ese paso. No improvisar cambios de negocio.

Comprobar antes del ensayo reservas futuras, comunicados vigentes/vencidos/lecturas, pagos total/parcial/pendiente y estados de incidentes en la foto nueva. Revisar los saldos con C5 y los reportes con servicios existentes; no sumar cartera como efectivo ni duplicar aporte del fondo por pago.

Tras integración y autorización de verificaciones, registrar controles sobre el mismo SHA:

```powershell
venv\Scripts\python.exe manage.py makemigrations --check
venv\Scripts\python.exe manage.py test apps --noinput
openspec validate --all --strict --no-interactive
```

Estos controles usan el entorno de desarrollo/pruebas MySQL, sin `--settings=config.settings_demo`. **No ejecutados en esta fase de prosa**; CI existente comprobada por SHA. La SQLite no reemplaza las pruebas MySQL. Arranque/cierre en 8016 según el guion; cerrar solo el servidor propio y dejar constancia del listener.

Guardar capturas integradas en una carpeta local ignorada, con nombre de ruta/rol/resolución y un índice SHA/fecha/base. Preparar respaldo accesible en el equipo de presentación; una captura de otra rama se identifica como tal. No incluir claves ni datos reales.

## Registro del ensayo y de la reunión

| Campo | Valor comprobado |
|---|---|
| Preparación documental | 16-nov-2026; agente de Walther, configuración de sesión gpt-6.1-sol / high |
| Participantes del ensayo | PENDIENTE |
| Fecha/hora efectiva de ensayo | PENDIENTE |
| Equipo, navegador y proyector usados | PENDIENTE |
| Conexión de presentación probada | PENDIENTE |
| SHA integrado final / CI / controles locales | PENDIENTE |
| Ruta y foto de datos final | PENDIENTE |
| Resultados por ruta, rol y resolución | PENDIENTE |
| Capturas integradas / respaldo accesible | PENDIENTE |
| Bloqueos resueltos y evidencia | PENDIENTE; ver bloqueos vigentes arriba |
| Hora real de congelamiento del recorrido | PENDIENTE; no se afirma congelamiento del 15-nov |
| Inicio y cierre de servidor 8016 del ensayo | PENDIENTE; esta sesión no levantó servidor |
| Reparto confirmado de expositores | PENDIENTE; propuesta en guion |
| Participantes y hora de reunión | PENDIENTE |
| Feedback, acuerdos y seguimiento de reunión | PENDIENTE |

## Estado de aceptación de #101

- [x] Guion de 12–15 min y versión breve, reparto propuesto y alternativas honestas.
- [x] Operación actual contrastada con código; cuentas ficticias y referencia a clave existente; limitación de base conservada explícita.
- [x] Pauta de feedback lista; alcance y compromisos se acuerdan después de la reunión.
- [x] Snapshot de main y CI existentes comprobados; matriz de ocho dependencias y bloqueos documentados.
- [ ] Ocho entregas terminadas/comprobadas e integraciones autorizadas realizadas.
- [ ] Foto aislada completa y coherente con el snapshot final.
- [ ] CI final y controles locales del conjunto, con evidencia del mismo SHA.
- [ ] Ensayo de equipo en conexión/equipo previstos, rutas/roles y ambas resoluciones.
- [ ] Capturas integradas de respaldo, acta final y congelamiento real registrados.

Entrega de esta fase: **PR borrador con Refs #101**. #101 permanece abierto; faltan integración y ensayo. El CI verde del PR documental validará su commit, sin acreditar las casillas pendientes.
