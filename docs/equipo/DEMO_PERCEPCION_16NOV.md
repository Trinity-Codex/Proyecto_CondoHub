# Demo de percepción · 16 de noviembre de 2026

Preparación de [#101](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/101).
**Estado al 16-nov: ensayo técnico local realizado; presentación y ensayo humano pendientes.** Código integrado `6c0fa2fd37393be436c5c779d46245d1138ead90`, CI verde. La [acta técnica](../demo_percepcion/ensayo-final.md) registra 81 GET, 56 capturas, cifras, límites y hallazgos. Proveedores se muestra en escritorio por la pérdida de contacto en móvil. No acredita ensayo del equipo/proyector/conexión del cliente, ni congelamiento retrospectivo.

## Objetivo y reparto

Primera conversación para mostrar la solución y entender necesidades; el alcance a medida y los compromisos se acuerdan después de la reunión. Vita Gestión, condominios, personas, correos y cifras son ejemplos ficticios. No presentar esta demo como aceptación final, producción desplegada o información del cliente.

Reparto propuesto, pendiente de confirmar asistencia: Walther conduce y muestra finanzas/cartera; Maximiliano muestra comunidad/reservas y toma notas en el bloque financiero; Winderson muestra pagos/incidentes y toma notas en comunidad. Walther registra las decisiones al cierre. Una sola persona opera el teclado por bloque; usar las cuentas del rol correspondiente.

## Recorrido de 12–15 minutos

Los tiempos incluyen transiciones. Abrir detalles desde las listas: los identificadores pueden cambiar entre bases. Verificar antes el condominio activo. El recorrido es principalmente de consulta; no emitir noviembre, registrar pagos ni modificar ejemplos durante la presentación.

| Minuto | Quién | Pantalla y mensaje | Alternativa si falta la pantalla o su evidencia |
|---|---|---|---|
| 0–1 | Walther | Acceso e inicio `/`: «Centralizamos comunidad y administración en un sitio accesible desde el celular. Todo lo mostrado es ficticio». Explicar roles y selector de condominio. | Usar la captura admin-inicio del snapshot indicado; explicar que es respaldo, no ejecución actual. |
| 1–3 | Maximiliano | Como administrador: `/condominio/unidades/`, `/comunicados/`, detalle desde lista. Mostrar unidad/edificio, comunicado general y dirigido; explicar lectura por unidad solo si el ejemplo está comprobado. | Si una publicación expiró, elegir otra vigente y conservar la explicación de destinatarios; no falsear la fecha. Hay comunicado dirigido con lectura comprobada. |
| 3–7 | Walther | `/gastos/`: septiembre/octubre emitidos y noviembre abierto. Abrir octubre desde la lista y `/gastos/reporte/`, seleccionando octubre de 2026. Explicar emitido, recaudado, saldo y deuda anterior; después `/gastos/fondo/` y movimientos. | Si las cifras difieren de la foto aprobada, omitir importes y detener ese bloque. Usar solo una captura identificada por SHA/fecha como respaldo, sin llamarla ejecución actual. |
| 7–8 | Walther | Cerrar sesión con el botón; entrar como gerencia y abrir `/cartera/?mes=2026-10`. Comparar ambos condominios para el mismo mes. Es consulta consolidada: gerencia no administra la comunidad ni ve nombres/RUT de residentes en esta vista. | Si gerencia no está comprobada, explicar la cartera sin usar superusuario para eludir permisos. Volver luego a la cuenta necesaria. |
| 8–10 | Winderson | Como administrador: `/pagos/cobranza/`, cuenta de unidad desde lista y `/proveedores/`. Mostrar un total, un abono y un pendiente ya existentes si están verificados. Registrar pago es función del administrador; comité consulta. | Mostrar proveedores en escritorio: en móvil se ocultan rubro/contacto/teléfono/correo, sin detalle para comité. Para pagos, Los Aromos tiene total, abono y pendiente comprobados; no registrar otro pago durante la presentación. |
| 10–12 | Maximiliano / Winderson | Como residente: `/pagos/mi-cuenta/`, `/reservas/`, `/reservas/mis-reservas/` y `/incidentes/`. Maximiliano explica disponibilidad/reserva; Winderson seguimiento de incidentes. Mostrar estados que existan y fechas vigentes. | Si la presentación ocurre después de las fechas verificadas, revisar primero vigencia y reservas; no presentar una reserva pasada como próxima. No mostrar datos con otro rol para salvar un 403. |
| 12–15 | Los tres | Preguntas de feedback, límites y siguiente paso. Walther confirma lo entendido; los colaboradores agregan observaciones de su bloque. | Si queda poco tiempo, priorizar las dos primeras preguntas de la pauta y acordar cómo completar las demás. |

Si una pantalla falla, no insistir ni editar en vivo: registrar ruta/rol/problema y seguir por la alternativa. El respaldo integrado está en `.demo_cliente/ensayo-6c0fa2f/`, con índice `mediciones.json` (rol, ruta, resolución, SHA y fecha). Usar esas capturas en lugar de las antiguas de #94. Comprobar su acceso en el equipo de presentación: sigue pendiente.

### Versión breve de 5–7 minutos

1. Walther, 1 min: visión, panel y roles.
2. Maximiliano, 1 min: comunidad y comunicado; explicar reservas si no hay ejemplo comprobado.
3. Walther, 2 min: octubre emitido, reporte y fondo; cartera solo si hay tiempo y sesión preparada.
4. Winderson, 1 min: cobranza e incidente existente, sin envíos.
5. Los tres, 1–2 min: problema principal del cliente, prioridad y límites. Anotar el resto para seguimiento.

## Operación local aislada

Referencia general: [DEMO_CLIENTE_LOCAL.md](../DEMO_CLIENTE_LOCAL.md). Para **esta foto integrada** usar el módulo temporal descrito aquí, no `config.settings_demo` directamente: este último apunta a la base anterior. Windows/PowerShell, Python 3.12, `venv` y dependencias de `requirements.txt` ya instaladas. No usar `iniciar.bat`, no editar `.env` ni operar la base habitual.

La foto nueva ya está preparada en este equipo. Ambos archivos siguientes son locales e ignorados:

- Settings: `.demo_cliente/settings_ensayo_6c0fa2f.py`.
- SQLite: `C:\Users\Walther\Desktop\Proyectos Claude\Proyecto_CondoHub\.demo_cliente\ensayo-6c0fa2f.sqlite3`.

El módulo contiene únicamente:

```python
from config.settings_demo import *
DATABASES["default"]["NAME"] = BASE_DIR / ".demo_cliente" / "ensayo-6c0fa2f.sqlite3"
```

Se creó con nombre nuevo después de comprobar la ruta resuelta dentro de `.demo_cliente/`, sin enlaces que salieran de ella y sin sobrescribir archivos. Conserva localhost, correo de consola y cookies demo. La base anterior `demo.sqlite3` está intacta, acreditada por hash y metadatos en el acta. No copiar estos artefactos a Git. En otro equipo, esta configuración/base no llegan con el PR: preparar allí una foto nueva y verificarla antes de presentar; no asumir que existe.

### Inicio en este equipo

Estos comandos usan la foto comprobada. El settings debe existir y su contenido/ruta coincidir con lo anterior. Revisar el SHA de código y que 8016 esté libre; si está ocupado, identificar al dueño sin detenerlo.

```powershell
Set-Location 'C:\Users\Walther\Desktop\Proyectos Claude\Proyecto_CondoHub'
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/heads/main
Get-Content .demo_cliente/settings_ensayo_6c0fa2f.py
Get-NetTCPConnection -State Listen -LocalPort 8016 -ErrorAction SilentlyContinue
```

Una sola sesión demo por perfil del navegador. Copiar este bloque completo a la terminal del servidor; guarda y restaura `PYTHONPATH` sin modificar variables permanentes:

```powershell
$pythonpathPrevio = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($pythonpathPrevio) {
        "$PWD\.demo_cliente;$pythonpathPrevio"
    } else {
        "$PWD\.demo_cliente"
    }
    venv\Scripts\python.exe manage.py preparar_demo_cliente --settings=settings_ensayo_6c0fa2f
    if ($LASTEXITCODE -ne 0) { throw 'Preparación fallida; no iniciar servidor' }
    venv\Scripts\python.exe manage.py runserver 127.0.0.1:8016 --settings=settings_ensayo_6c0fa2f --noreload
} finally {
    $env:PYTHONPATH = $pythonpathPrevio
}
```

El wrapper debe anunciar `django.db.backends.sqlite3` y la ruta **ensayo-6c0fa2f.sqlite3** indicada arriba antes de migrar/cargar. Si no coincide, detenerse. No reemplazarlo por comandos sin protección. La repetición conserva datos: se comprobó igualdad de todas las tablas antes/después de la segunda preparación. No usar `--reiniciar`, borrar, mover ni sustituir bases.

Abrir [la demo local](http://127.0.0.1:8016/). `ALLOWED_HOSTS` admite `127.0.0.1`. El correo es de consola; no afirmar entrega externa. La preparación puede mostrar la clave demo existente: no copiarla a logs compartidos, capturas ni notas. Los logs de evidencia omiten esa línea.

Las cookies están separadas del entorno habitual, pero se comparten entre puertos que usen estos settings. El ensayo cargó estilos reales: variable Bootstrap `--bs-body-font-size=1rem`, íconos y fuentes comprobados, sin fallback inyectado ni errores de consola registrados. Esto no prueba la conexión del lugar: equipo, navegador, proyector y conexión del cliente siguen **PENDIENTES**. No prometer funcionamiento sin internet.

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

Vista Verde: apertura $1.000.000 al 31-ago + aportes $110.476 y $105.061 − egreso ficticio $75.000 = $1.140.537. Los Aromos: apertura $500.000 + aporte $33.925 = $533.925. Son movimientos contables del fondo, **no efectivo recaudado**. Los pagos no generan un segundo aporte; la cartera representa el mes seleccionado, no una caja consolidada. En la foto nueva integrada, Los Aromos recauda $416.213 en octubre. Cartera de octubre: emitido $2.918.700, recaudado $1.663.475; no sumar septiembre al mismo corte mensual.

### Base existente y recuperación segura

Repetir `preparar_demo_cliente` migra y conserva registros: no duplica ni regenera. Si ya existe algún condominio demo, `cargar_demo` retorna antes de llamar los loaders. Por eso **un PR nuevo de datos no aparece solo por repetir la preparación**. La advertencia del cargador puede mencionar `--reiniciar`; no seguir esa sugerencia para resolver este ensayo.

Ante un error: conservar la base y el mensaje (sin claves), identificar SHA/settings/ruta y corregir la causa antes de repetir. No borrar, reiniciar ni sustituir la SQLite actual; tampoco tocar desarrollo.

La vía segura ya se ejecutó: configuración temporal y SQLite nueva `ensayo-6c0fa2f.sqlite3`, conservando la anterior. Si llegan más loaders, no cambiar de nombre ni preparar otra foto de forma improvisada: conservar ésta, elegir otra ruta nueva dentro de `.demo_cliente/` y verificar de nuevo código/configuración/carga/evidencia. No sobrescribir las capturas del snapshot comprobado.

### Cierre

Cerrar sesión con el botón, detener **este** servidor con `Ctrl+C` en su terminal y confirmar:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8016 -ErrorAction SilentlyContinue
```

No debe quedar un listener propio en 8016; si aparece otro proceso, identificarlo sin terminarlo. Conservar la base, acta y evidencias locales. No usar cierres masivos de Python ni borrar archivos para limpiar la demo.

## Límites para comunicar

- Auditoría: núcleo/eventos integrados, pantalla todavía provisional y solo administrador; comité recibe 403. El menú mantiene «En preparación». No mostrarla como historial terminado ni habilitar permisos por una entrega local todavía sin PR integrado.
- Rendición: pantalla provisional, pendiente de #55.
- Aviso de cobro PDF (#6) y comprobante (#56): no presentarlos como disponibles. El helper PDF existente no equivale a esas funciones.
- Anulación de pagos (#53) y avisos por residencia (#46): PR #73/#74 ya unidos. El ejemplo de A-101 en octubre contiene un pago anulado con motivo ficticio: no rebaja el saldo, que sigue en $264.754. Se muestra como consulta; no anular ni registrar pagos durante la demo. No confundir esta función con el PDF/comprobante aún pendientes.
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
