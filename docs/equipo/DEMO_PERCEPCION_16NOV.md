# Demo de percepción · 16 de noviembre de 2026

Preparación de [#101](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/101).
**Estado al 16-nov: presentación pendiente; ensayo integrado pendiente.** Este guion está preparado para revisión; su uso depende de las pantallas comprobadas antes de la reunión. La [acta de preparación](../demo_percepcion/ensayo-final.md) identifica el SHA, las entregas y los bloqueos. No acredita un ensayo el domingo 15 ni un congelamiento retrospectivo.

## Objetivo y reparto

Primera conversación para mostrar la solución y entender necesidades; el alcance a medida y los compromisos se acuerdan después de la reunión. Vita Gestión, condominios, personas, correos y cifras son ejemplos ficticios. No presentar esta demo como aceptación final, producción desplegada o información del cliente.

Reparto propuesto, pendiente de confirmar asistencia: Walther conduce y muestra finanzas/cartera; Maximiliano muestra comunidad/reservas y toma notas en el bloque financiero; Winderson muestra pagos/incidentes y toma notas en comunidad. Walther registra las decisiones al cierre. Una sola persona opera el teclado por bloque; usar las cuentas del rol correspondiente.

## Recorrido de 12–15 minutos

Los tiempos incluyen transiciones. Abrir detalles desde las listas: los identificadores pueden cambiar entre bases. Verificar antes el condominio activo. El recorrido es principalmente de consulta; no emitir noviembre, registrar pagos ni modificar ejemplos durante la presentación.

| Minuto | Quién | Pantalla y mensaje | Alternativa si falta la pantalla o su evidencia |
|---|---|---|---|
| 0–1 | Walther | Acceso e inicio `/`: «Centralizamos comunidad y administración en un sitio accesible desde el celular. Todo lo mostrado es ficticio». Explicar roles y selector de condominio. | Explicar la visión con este guion; no atribuir a main el pulido de PR abiertos. |
| 1–3 | Maximiliano | Como administrador: `/condominio/unidades/`, `/comunicados/`, detalle desde lista. Mostrar unidad/edificio, comunicado general y dirigido; explicar lectura por unidad solo si el ejemplo está comprobado. | Sin #95/#96/#99 verificados, mostrar únicamente las listas revisadas o describir el flujo; no prometer publicaciones recientes o lectura precargada. |
| 3–7 | Walther | `/gastos/`: septiembre/octubre emitidos y noviembre abierto. Abrir octubre desde la lista y `/gastos/reporte/`, seleccionando octubre de 2026. Explicar emitido, recaudado, saldo y deuda anterior; después `/gastos/fondo/` y movimientos. | Si las cifras difieren de la foto aprobada, omitir importes y detener ese bloque. Usar solo una captura identificada por SHA/fecha como respaldo, sin llamarla ejecución actual. |
| 7–8 | Walther | Cerrar sesión con el botón; entrar como gerencia y abrir `/cartera/?mes=2026-10`. Comparar ambos condominios para el mismo mes. Es consulta consolidada: gerencia no administra la comunidad ni ve nombres/RUT de residentes en esta vista. | Si gerencia no está comprobada, explicar la cartera sin usar superusuario para eludir permisos. Volver luego a la cuenta necesaria. |
| 8–10 | Winderson | Como administrador: `/pagos/cobranza/`, cuenta de unidad desde lista y `/proveedores/`. Mostrar un total, un abono y un pendiente ya existentes si están verificados. Registrar pago es función del administrador; comité consulta. | Los pagos de Los Aromos de #98 no están en main: elegir ejemplos existentes de Vista Verde comprobados antes, o explicar el flujo sin inventar recaudación. El formulario puede mostrarse sin enviarlo. |
| 10–12 | Maximiliano / Winderson | Como residente: `/pagos/mi-cuenta/`, `/reservas/`, `/reservas/mis-reservas/` y `/incidentes/`. Maximiliano explica disponibilidad/reserva; Winderson seguimiento de incidentes. Mostrar estados que existan y fechas vigentes. | Sin reservas futuras de #96 o incidente resuelto de #98, describirlos como ejemplos pendientes de integrar. Si el residente no está verificado, omitir la navegación; no mostrar datos con otro rol como sustituto. |
| 12–15 | Los tres | Preguntas de feedback, límites y siguiente paso. Walther confirma lo entendido; los colaboradores agregan observaciones de su bloque. | Si queda poco tiempo, priorizar las dos primeras preguntas de la pauta y acordar cómo completar las demás. |

Si una pantalla falla, no insistir ni editar en vivo: registrar ruta/rol/problema y seguir por la alternativa. Las capturas financieras de #94 pertenecen a su rama, no a una integración completa. Las capturas integradas de respaldo siguen pendientes según el acta.

### Versión breve de 5–7 minutos

1. Walther, 1 min: visión, panel y roles.
2. Maximiliano, 1 min: comunidad y comunicado; explicar reservas si no hay ejemplo comprobado.
3. Walther, 2 min: octubre emitido, reporte y fondo; cartera solo si hay tiempo y sesión preparada.
4. Winderson, 1 min: cobranza e incidente existente, sin envíos.
5. Los tres, 1–2 min: problema principal del cliente, prioridad y límites. Anotar el resto para seguimiento.

## Operación local aislada

Referencia de operación: [DEMO_CLIENTE_LOCAL.md](../DEMO_CLIENTE_LOCAL.md). Usar Windows/PowerShell en la raíz del repositorio, Python 3.12 y `venv` con las dependencias de `requirements.txt` ya instaladas. Git y conexión a GitHub sirven para verificar el snapshot. MySQL se usa en los controles de desarrollo/CI; la demo usa su SQLite exclusiva. No usar `iniciar.bat` para este recorrido: arranca el entorno habitual.

Equipo, navegador, proyector, conexión y hora real de la reunión: **PENDIENTE de confirmar/probar**. Bootstrap, íconos y fuentes tienen recursos externos: probar la conexión del lugar; no prometer funcionamiento sin internet. No alterar `.env` ni la base habitual.

### Antes de arrancar

```powershell
Set-Location 'C:\Users\Walther\Desktop\Proyectos Claude\Proyecto_CondoHub'
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/main
Get-NetTCPConnection -State Listen -LocalPort 8016 -ErrorAction SilentlyContinue
```

Registrar el SHA de código que se usará y su CI en el acta. Si 8016 está ocupado, no detener el proceso: identificar su dueño y coordinar. No utilizar 8000 ni cerrar servidores ajenos. No cambiar de rama mientras otra sesión esté trabajando. Las uniones requieren una decisión expresa de Walther; este documento no autoriza merge.

### Preparar y servir

Ejecutar la preparación, revisar su salida y continuar solo si terminó correctamente:

```powershell
venv\Scripts\python.exe manage.py preparar_demo_cliente --settings=config.settings_demo
```

Debe anunciar `django.db.backends.sqlite3` y exactamente:

```text
C:\Users\Walther\Desktop\Proyectos Claude\Proyecto_CondoHub\.demo_cliente\demo.sqlite3
```

El comando valida aislamiento antes de migrar/cargar. Si falla, detenerse y revisar la causa; no sustituirlo por `migrate` o `cargar_demo` sin los settings de demo. Con resultado correcto, en su propia terminal:

```powershell
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8016 --settings=config.settings_demo
```

Abrir [la demo local](http://127.0.0.1:8016/). `ALLOWED_HOSTS` admite `127.0.0.1`; usar esa dirección. El correo se imprime en consola, no se demuestra entrega externa. Las cookies demo están separadas del entorno habitual, pero se comparten entre puertos que usen estos mismos settings: evitar sesiones demo paralelas con roles distintos en el mismo perfil del navegador.

### Cuentas ficticias

La clave se consulta únicamente en la sección [Usuarios de demostración del README](../../README.md#usuarios-de-demostración); no copiarla a guiones, capturas, registros ni mensajes.

| Correo ficticio | Uso |
|---|---|
| `administrador@condohub.cl` | Administración de Vista Verde y Los Aromos; selector de condominio. |
| `comite@condohub.cl` | Consulta financiera; también residente de A-201. No usarlo como prueba de un rol exclusivamente residente. |
| `conserje@condohub.cl` | Operación permitida; sin información financiera. |
| `residente@condohub.cl` | Perspectiva de residente de A-101. |
| `residente2@condohub.cl` | Residente de B-102, si se compara visibilidad por edificio. |
| `residente3@condohub.cl` | Residente de Los Aromos, si sus ejemplos están comprobados. |
| `gerencia@condohub.cl` | Cartera de ambos condominios; sin membresía de administración dentro de ellos. |
| `superadmin@condohub.cl` | Administración de plataforma; fuera del recorrido comercial propuesto. |

Cambiar de cuenta mediante el botón de cierre de sesión (POST), luego iniciar sesión como el rol requerido. No navegar al logout por GET ni usar superusuario para salvar un 403. Confirmar cuenta y condominio después de cada transición.

### Fecha y cifras de referencia

`DEMO_FECHA_REFERENCIA` es **16-nov-2026**. Fija los ejemplos de carga, no congela el reloj de las vistas: reservas próximas y vigencia se contrastan con la fecha real del ensayo. Si se presenta otro día, volver a verificar; no cambiar el reloj para ocultar ejemplos vencidos.

| Condominio ficticio | Períodos de la foto #93 | Fondo contable esperado |
|---|---|---|
| Vista Verde | Septiembre y octubre de 2026 emitidos; noviembre abierto | $1.140.537 |
| Los Aromos | Octubre de 2026 emitido | $533.925 |

Vista Verde: apertura $1.000.000 al 31-ago + aportes $110.476 y $105.061 − egreso ficticio $75.000 = $1.140.537. Los Aromos: apertura $500.000 + aporte $33.925 = $533.925. Son movimientos contables del fondo, **no efectivo recaudado**. Los pagos no generan un segundo aporte; la cartera representa el mes seleccionado, no una caja consolidada. En main, Los Aromos aún no tiene los pagos extra de #98: no usar los $416.213 del QA de su rama como recaudación integrada.

### Base existente y recuperación segura

Repetir `preparar_demo_cliente` migra y conserva registros: no duplica ni regenera. Si ya existe algún condominio demo, `cargar_demo` retorna antes de llamar los loaders. Por eso **un PR nuevo de datos no aparece solo por repetir la preparación**. La advertencia del cargador puede mencionar `--reiniciar`; no seguir esa sugerencia para resolver este ensayo.

Ante un error: conservar la base y el mensaje (sin claves), identificar SHA/settings/ruta y corregir la causa antes de repetir. No borrar, reiniciar ni sustituir la SQLite actual; tampoco tocar desarrollo.

Vía segura para los nuevos datos, **pendiente de definir y verificar tras las integraciones**: conservar la base actual y preparar una SQLite con nombre nuevo dentro de `.demo_cliente/` (por ejemplo `ensayo-integrado-<SHA>.sqlite3`), mediante una configuración temporal explícita usada tanto en preparación como en servidor. Los settings actuales fijan `demo.sqlite3` y no ofrecen una opción CLI para cambiarla: no inventar una bandera. Revisar esa operación por separado antes de ejecutarla; registrar motor/ruta/SHA y comprobar la foto completa. Mientras falte, usar solo los ejemplos existentes verificados y comunicar la limitación.

### Cierre

Cerrar sesión con el botón, detener **este** servidor con `Ctrl+C` en su terminal y confirmar:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8016 -ErrorAction SilentlyContinue
```

No debe quedar un listener propio en 8016; si aparece otro proceso, identificarlo sin terminarlo. Conservar la base, acta y evidencias locales. No usar cierres masivos de Python ni borrar archivos para limpiar la demo.

## Límites para comunicar

- Auditoría: existe el núcleo de registro/eventos; la pantalla sigue provisional. No mostrarla como un historial terminado.
- Rendición: pantalla provisional, pendiente de #55.
- Aviso de cobro PDF (#6) y comprobante (#56): no presentarlos como disponibles. El helper PDF existente no equivale a esas funciones.
- Anulación de pagos (#53): PR #73 abierto en borrador; no está integrada. PR #74 también sigue borrador y no altera el comportamiento de notificación de main.
- PWA: hay manifest e íconos; funcionamiento sin conexión (#26) pendiente. No cortar internet como demostración.
- Despliegue (#29), respaldo (#50) y prueba guiada formal (#59) conservan su alcance propio; esta preparación no los implementa ni los cierra.

## Pauta de feedback

Introducción de Walther: «Queremos entender su trabajo antes de acordar el alcance. Tomaremos notas; las solicitudes se priorizarán después de la reunión». No pedir datos personales, claves o archivos reales durante la demo.

| Tema | Pregunta | Qué registrar |
|---|---|---|
| Tarea actual | ¿Qué tarea les toma más tiempo hoy y cómo la resuelven? ¿Quién participa y con qué frecuencia? | Flujo, actor, herramientas y dificultad concreta. |
| Prioridad | De lo visto, ¿qué dos problemas conviene resolver primero y por qué? | Orden, impacto y motivo; separar necesidad de sugerencia visual. |
| Datos/reportes | ¿Qué información necesitan consultar, con qué corte y quién la recibe? ¿Qué exportan hoy? | Campos, período, formato y permisos necesarios; pedir después una muestra anonimizada si corresponde. |
| Vocabulario | ¿Cómo llaman a los gastos, cobros, abonos, morosidad, unidades y fondo? | Término actual, alternativa sugerida y significado. |
| Uso | ¿Desde qué equipos y en qué condiciones de conexión trabajan? ¿Qué pantalla resultó confusa? | Dispositivo, contexto y paso observado. |

Plantilla para tomar notas (sin comprometer entrega):

| Observación o frase del cliente | Necesidad a validar | Prioridad propuesta | Responsable de aclarar | Próximo paso / fecha acordada |
|---|---|---|---|---|
| PENDIENTE de reunión | PENDIENTE | PENDIENTE | PENDIENTE | PENDIENTE |

Cerrar leyendo dos o tres necesidades para confirmar entendimiento. Después, el equipo revisa viabilidad, alcance, estimación y permisos; Walther consolida la propuesta y acuerda compromisos con el cliente. No prometer funcionalidades ni fechas durante el recorrido. Registrar participantes, decisiones y seguimiento después de que ocurran, sin rellenar resultados anticipadamente.
