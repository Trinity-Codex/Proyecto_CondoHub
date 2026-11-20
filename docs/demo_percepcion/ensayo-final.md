# Acta de ensayo técnico local · #101

**Ensayo técnico realizado; ensayo humano y aprobación final de demo PENDIENTES.** Fecha: 16-nov-2026, America/Santiago. Preparación de la foto a las 18:11; capturas entre **18:17** y **18:37**. No se afirma reunión realizada, ensayo de los tres integrantes ni congelamiento del domingo 15.

Guion, operación y feedback: [DEMO_PERCEPCION_16NOV.md](../equipo/DEMO_PERCEPCION_16NOV.md). [Issue #101](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/101) permanece abierto y [PR #107](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/107) borrador, con `Refs #101`. El contacto de proveedores en móvil sigue como hallazgo; se usa escritorio, sin presentarlo como corregido.

## Snapshot y alcance

- Código de producto ensayado: main `6c0fa2fd37393be436c5c779d46245d1138ead90`, verificado contra GitHub. [CI de main 43938313918](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/runs/43938313918): SUCCESS, 790 pruebas y OpenSpec 12/12 según evidencia revisada del orquestador.
- Se actualizó `codex/101-guion-ensayo-demo` con `origin/main` conservando `39dacc1`; merge local de la rama documental `024140f4ac1294ad71a58eeec667405eec4997fc`. Diferencia de producto respecto de main: ninguna; el PR mantiene solo estos dos documentos. No se unió PR107 ni se modificaron carpetas ajenas.
- El SHA documental definitivo y su CI se registran en el PR y en `.codex/orquestador/notas/n101-ensayo-tecnico.md` al publicar. La CI de main prueba el producto integrado; la CI de PR107 se espera sobre el nuevo head. No se vuelve a ejecutar toda la suite local por prosa.
- Todo condominio, persona, RUT, correo y monto es ficticio. Sin cambios de producto, datos de desarrollo, `.env`, reloj, permisos o menú. Solo preparación nueva autorizada, consultas y login/logout; no se enviaron operaciones financieras ni formularios de producto durante la navegación.

## Ocho dependencias integradas

Estados y squash comprobados con `gh pr view` y estado de Issues. Todos están en el snapshot de código citado. «Unido» no convierte sus QA individuales en ensayo del equipo físico.

| Issue / responsable | Entrega | PR | Squash integrado | Estado |
|---|---|---|---|---|
| [#93](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/93) · Walther | Aislamiento y finanzas | [PR #102](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/102) | `6eaa59e2acd48847d8348359ed32a008a310814e` | Unido; Issue cerrado |
| [#94](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/94) · Walther | Pulido compartido y financiero | [PR #106](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/106) | `5d8f2660789d069a4d0c68e3709bd1554a8c7d41` | Unido; Issue cerrado |
| [#95](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/95) · Maximiliano | Acceso, comunidad, panel y reservas | [PR #108](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/108) | `a12328c1a0cd63060ac7cf2a780b5f3a22b1870a` | Unido; Issue cerrado |
| [#96](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/96) · Maximiliano | Actividad ficticia de comunidad/reservas | [PR #109](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/109) | `f9733583b65b0deca3cda7ee5037297d55aec14b` | Unido; Issue cerrado |
| [#97](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/97) · Winderson | Pulido de pagos/proveedores/incidentes | [PR #104](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/104) | `4cdddf63f2b5da6cf73246b681f94d03dba91311` | Unido; Issue cerrado |
| [#98](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/98) · Winderson | Datos de operación y pagos | [PR #103](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/103) | `e4bb7d3a080d88ea2da62bd255ad409094a7dfef` | Unido; Issue cerrado |
| [#99](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/99) · Maximiliano | QA comunidad/residente | [PR #110](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/110) | `6c0fa2fd37393be436c5c779d46245d1138ead90` | Unido; Issue cerrado |
| [#100](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/100) · Winderson | QA operación/finanzas | [PR #105](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/105) | `4e1c93785a7ceb74f509c8c319d5920b8726d8f7` | Unido; Issue cerrado |

Además, [PR #73](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/73) (anulación) está unido en `6759c9b3f8f5b1c5893bbc1dcbdc14e3424c4e4c` y [PR #74](https://github.com/Trinity-Codex/Proyecto_CondoHub/pull/74) (avisos por residencia) en `4c89c113fa0178d8612ba95c8a8b308565402377`. Se corrige el límite anterior que los llamaba borradores. PDF/comprobante no se deducen de esas uniones.

Los informes históricos de #99/#100 describen sus propias ramas/bases; #99 declaró fallback local de Bootstrap. Esta acta aporta evidencia nueva del conjunto y navegador real, sin atribuir a main sus mediciones antiguas ni sustituir la prueba guiada formal #59.

## Foto nueva y conservación

Settings temporal ignorado `.demo_cliente/settings_ensayo_6c0fa2f.py`, heredado de `config.settings_demo` con un solo cambio: `DATABASES["default"]["NAME"]` a **`.demo_cliente/ensayo-6c0fa2f.sqlite3`**. Ruta absoluta comprobada dentro de `.demo_cliente/`, sin enlaces salientes ni archivo preexistente al crear. Mismo módulo para preparar y servir; `PYTHONPATH` limitado a esos procesos y restaurado mediante `finally`.

El wrapper `preparar_demo_cliente --settings=settings_ensayo_6c0fa2f` anunció SQLite y esa ruta antes de migrar/cargar. Primera preparación creó la foto; segunda preparación conservó conteos y hash de contenido de **todas las tablas** (`idempotencia.json`, antes/después iguales). No se usó `--reiniciar` ni se borró, movió o sustituyó una base.

La SQLite anterior `.demo_cliente/demo.sqlite3` conserva exactamente bytes (499.712), fecha de modificación y SHA-256:

```text
5609e3b3e224bc8f1381082f551580f5d94336ec9464ae1672569b6014d75ae7
```

Evidencia: `base-anterior-antes.json` y `base-anterior-despues.json`. Comparación adicional de tablas de la foto nueva tras navegar: solo cambió `cuentas_usuario` por último acceso; tablas de negocio idénticas a la foto posterior a preparación. Los logins crearon/cerraron sesiones normales; no hubo registros de pagos, anulaciones, reservas o comunicados nuevos durante el ensayo.

### Inventario y cifras comprobadas

| Condominio / período | Estado | Emitido | Recaudado = pagos vigentes = suma por cobro | Aporte único al fondo |
|---|---|---|---|---|
| Vista Verde 09/2026 | Emitido | $2.320.001 | $1.948.801 | $110.476 |
| Vista Verde 10/2026 | Emitido | $2.206.275 | $1.247.262 | $105.061 |
| Vista Verde 11/2026 | Abierto | No emitido | No se cobra | Sin ingreso de emisión |
| Los Aromos 10/2026 | Emitido | $712.425 | $416.213 | $33.925 |

Verificación con `generar_reporte`, `pagado_del_cobro`, `Pago.objects.vigentes()`, `saldo_fondo` y `armar_cartera`, sin recalcular reglas de negocio. Un solo ingreso por período emitido, igual a la suma de aportes de sus cobros. Fondo Vista Verde **$1.140.537** y Los Aromos **$533.925**; son saldos contables, no efectivo. Cartera de octubre: emitido **$2.918.700**, recaudado **$1.663.475**.

- Los Aromos: o-101/o-102 pagados, o-201 con abono de $60.000, o-202 pendiente. Proveedores activos: 3 en Vista Verde y 2 en Los Aromos.
- A-101 de Vista Verde: un pago de octubre anulado con motivo ficticio; pagado vigente $0 y saldo pendiente $264.754. Se verificó en el detalle del residente, sin ejecutar otra anulación.
- Incidentes Vista Verde: recibido, en proceso y resuelto, con seguimiento ficticio.
- Cinco comunicados: general reciente, dirigido a Torre A con lectura confirmada y vencido de Torre B en su filtro. Sin publicaciones futuras. Los ejemplos nuevos vencen el 23-nov.
- Tres reservas confirmadas próximas al momento del ensayo: Gimnasio 18-nov 07:00–08:00 (comité/A-201), Quincho 19-nov 13:00–17:00 (residente/A-101) y Salón 20-nov 19:00–23:00 (residente2/B-102). No se falseó el reloj. Revalidar si cambia el día de presentación.

Detalle de casos, fechas y cifras: `inventario.json`. La primera consulta de verificación usó por error el nombre `Pago.cobro`; se corrigió a la relación real `Pago.detalle` y se ejecutaron las aserciones con éxito, sin modificar producto ni volver a cargar datos.

## Ensayo técnico y resultados

### Permisos y aislamiento

**81 GET de Django Client**, sobre la nueva SQLite y código integrado, con autenticación ficticia normal y sesiones por rol/condominio: **81 códigos esperados, 0 discrepancias, 0 errores 500**. No son 81 navegaciones de navegador; la evidencia separa ambos métodos.

| Rol/contexto | Casos GET | Qué se contrastó |
|---|---|---|
| Administrador Vista Verde | 20 | Inicio/comunidad/finanzas/operación, consulta provisional Auditoría/Rendición; cartera sin asignación 403 y objetos Los Aromos 404. |
| Administrador Los Aromos | 8 | Inicio, cobranza, fondo, período/comunicado propio y proveedores 200; período/comunicado de Vista Verde 404. |
| Comité | 12 | Consulta financiera/proveedores 200; crear pago/proveedor/egreso y Auditoría 403; cobro ajeno 404. Su rol adicional residente está identificado. |
| Conserje | 8 | Inicio/incidentes/reservas 200; fondo/reporte/cobranza/proveedores/Auditoría 403. |
| Residente Vista Verde | 14 | Cuenta/cobro propio, comunicado dirigido y reserva propios; cobro, comunicado o espacio ajenos 404; administración financiera/proveedores 403. |
| Residente Los Aromos | 9 | Cuenta/cobro/comunicado/espacio propios 200; objetos Vista Verde 404. |
| Gerencia | 6 | Cartera y reportes de los dos asignados 200; comunidad/fondo redirigen por ausencia de membresía. |
| Sin sesión | 4 | Login y privacidad 200; inicio/cuenta protegidos redirigen. |

Matriz completa esperado/observado/URL/redirección: `rutas-roles.json`. Los 403/404 esperados son controles correctos, no errores de demo.

### Navegador real, capturas y recursos

Navegador integrado Chromium, servidor propio `127.0.0.1:8016`, mismo settings/base, login/logout reales como administrador, residente, gerencia, comité y conserje. **56 capturas y 56 mediciones**, incluidas dos de foco; resoluciones **1440x900 y 375x812**, 0 casos con `scrollWidth > innerWidth`. Los 15 px menos en algunas páginas corresponden a la barra vertical; tablas pueden desplazar internamente.

| Cuenta | Pantallas capturadas en ambos tamaños |
|---|---|
| Administrador | Inicio, gastos, octubre emitido, reporte, fondo, unidades, comunicado leído, vencidos, todas las reservas, cobranza, proveedores, incidente resuelto y formulario de egreso sin envío. |
| Residente | Inicio, Mi cuenta, cobro con pago anulado, comunicado dirigido leído, disponibilidad del Quincho, Mis reservas e incidentes. |
| Gerencia | Cartera de octubre y reporte de Los Aromos. |
| Comité | Proveedores y 403 esperado de Auditoría. |
| Conserje | Inicio sin tarjetas financieras y 403 esperado del fondo. |
| Sin sesión | Acceso; más una captura de foco por Tab. |

Recorrido servido: **59 respuestas HTTP registradas**, incluidas navegación y login/logout, sin 500; `respuestas-http.json` y `servidor.log`. No se detectaron enlaces rotos en los pasos recorridos, sin afirmar un rastreo exhaustivo de todos los enlaces del producto.

Estilos usados desde las referencias reales del sitio: Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Google Fonts y CSS local. Variable computada `--bs-body-font-size=1rem`, padding Bootstrap, fuente Montserrat e íconos `bootstrap-icons` observados; consola sin errores/avisos capturados. No se inyectó copia local ni se quitó SRI. La propiedad `link.sheet` no resultó fiable en el DOM acotado del navegador; no se usó como prueba de carga fallida. Esta comprobación no valida la conexión del cliente ni el modo sin internet.

En controles inspeccionados dentro de `main`, cero campos sin etiqueta asociada/ARIA. Se ejercitó Tab y se conservaron capturas de foco/formulario/acceso; las mediciones inmediatas de outline/sombra no bastan para aprobar contraste de foco. **No se acredita auditoría WCAG, contraste completo ni estados de error de formularios**: no se enviaron formularios de producto. Esos puntos se revisan manualmente antes de la presentación.

### Evidencia persistente

Carpeta local ignorada **`.demo_cliente/ensayo-6c0fa2f/`**, conservada con la SQLite y el settings en su directorio padre:

- `mediciones.json`: índice de 56 JPG con rol, URL, resolución, fecha y SHA de código. Ejemplos: `admin-inicio-1440.jpg`, `admin-fondo-375.jpg`, `residente-cobro-anulado-375.jpg`, `gerencia-cartera-1440.jpg`, `comite-proveedores-375.jpg`.
- `inventario.json`, `idempotencia.json`, `rutas-roles.json`, `respuestas-http.json`, `dependencias.json` y `conservacion-negocio.json`.
- `preparacion-1.log` y `preparacion-2.log`, sin la línea de clave demo; `servidor.log` y registro de 403 esperados.
- `base-anterior-antes.json` / `base-anterior-despues.json`, `hallazgo-proveedores.json`, `recursos.json`, `foco-formulario.json` y `foco-acceso.json`.

El navegador solo pudo escribir inicialmente en la carpeta permitida de visualizaciones de este chat. Se copiaron los JPG/JSON a la carpeta persistente anterior con escalación normal; ya no dependen de temporales. No se agregan a Git ni se copian claves o datos reales. Comprobar acceso al respaldo en el equipo físico de presentación sigue pendiente.

## Hallazgos y límites vigentes

| Hallazgo / límite | Evidencia y consecuencia | Responsable / alternativa |
|---|---|---|
| Contacto móvil de proveedores incompleto | A 375 px Rubro/Contacto tienen `display:none`, incluidos teléfono/correo. Comité no tiene enlace de edición ni detalle alternativo. A 1440 están visibles. No se corrige ni se aprueba como resuelto por ausencia de desborde. | Winderson, gestión fuera de PR107. Mostrar proveedores en escritorio; si solo hay móvil, omitir consulta de contacto y explicar el límite. |
| Auditoría sigue provisional | Código y GET: administrador 200 provisional; comité 403; menú conserva «En preparación». Al cierre solo PR107/68 abiertos, sin vista nueva publicada/integrada. PR72/90 entregaron núcleo/eventos. | Winderson: futuro PR de vista con menú/permisos/prueba coherentes; Walther decide unión. No anticipar habilitación en PR107. |
| Rendición / PDF / comprobante / offline | Rendición provisional; helper PDF no equivale a aviso/comprobante construidos. Manifest/íconos no prueban modo sin conexión. | Mantener próximos pasos de #55/#6/#56/#26. No simular funciones. |
| Equipo/proyector/conexión, foco/errores y ensayo humano | Solo ensayo técnico local; no estuvieron comprobados los medios reales de presentación ni la presencia física del equipo. | Los tres, coordinados por Walther: prueba manual antes de presentar. No declarar aprobación global con estos pendientes. |

No retomar #29/#50 ni cerrar #59. El reparto Walther/Maximiliano/Winderson sigue propuesto, pendiente de confirmar disponibilidad; Walther puede conducir el recorrido si falta un expositor, sin dar por confirmada su asistencia.

## Registro operativo y pendientes humanos

| Campo | Estado |
|---|---|
| Preparación, foto nueva y ensayo técnico | REALIZADOS el 16-nov; evidencia citada, sin escrituras de negocio durante navegación. |
| Inicio / cierre de servidor propio | 8016, `--noreload`; sesión propia detenida con Ctrl+C. Comprobación final: sin listener8016; no se detuvieron procesos ajenos. |
| Conservación de base anterior / datos de negocio | COMPROBADA por hash/metadatos y huellas de tablas. |
| Participantes y hora de ensayo humano | PENDIENTE |
| Equipo, navegador físico y proyector | PENDIENTE |
| Conexión del lugar y respaldo accesible allí | PENDIENTE |
| Revisión manual de foco/errores en medios reales | PENDIENTE |
| Resolución definitiva del contacto móvil de proveedores | PENDIENTE fuera de PR107; alternativa escritorio documentada. |
| Reparto confirmado / disponibilidad de Maximiliano | PENDIENTE |
| Congelamiento real del recorrido | PENDIENTE; no se inventa cumplimiento del domingo15. |
| Participantes/hora/feedback/acuerdos de la reunión | PENDIENTE; pauta lista en guion. |

Antes de presentar: confirmar participantes/dispositivo/conexión, arrancar con los comandos exactos del guion y la **base nueva**, recorrer las pantallas elegidas, usar proveedores en escritorio, comprobar respaldo/foco/errores y registrar hora real de congelamiento. Al acabar, logout, Ctrl+C del servidor propio y conservar archivos. Ninguna base debe borrarse para repetir.

## Estado de aceptación de #101

- [x] Ocho entregas previas unidas/comprobadas, snapshot y CI de código identificados.
- [x] Foto nueva aislada, repetición sin cambios, importes coherentes y datos ficticios actuales.
- [x] Ensayo técnico con matriz por rol/aislamiento, navegador real en ambos tamaños y capturas persistentes.
- [x] Guion 12–15 min y breve, operación concreta de nueva ruta/settings/PYTHONPATH, feedback y límites actualizados.
- [ ] Contacto móvil de proveedores resuelto o decisión explícita sobre ese límite; no se afirma demo sin defectos.
- [ ] Ensayo humano con equipo/proyector/conexión previstos y respaldo accesible.
- [ ] Revisión manual pendiente de foco/errores, reparto confirmado y congelamiento real registrados.
- [ ] Acta humana completada con participantes, medios y acuerdos cuando ocurran. El resultado de CI del nuevo head se registra en PR107 y en la nota de entrega al publicar.

Esta fase termina con actualización de **PR107 borrador / Refs #101**, sin merge ni cierre de #101. El CI documental y el ensayo técnico no completan por sí solos los criterios humanos pendientes.
