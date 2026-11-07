# Winderson Castrillo — Plan de trabajo del PMV (7 al 27 de noviembre)

Plan general del equipo: [PLAN_PMV_27NOV.md](PLAN_PMV_27NOV.md). Este documento es tu hoja de ruta y la de tu
agente de IA: qué haces, en qué orden, con qué modelo y con cuánto esfuerzo.

**Tus carpetas** (solo tú las modificas durante el PMV): `apps/pagos`, `apps/proveedores`, `apps/incidentes`,
`apps/auditoria` y `apps/rendicion` (ambas las crea #62) y el service worker en `static/`.

**Tus contratos** (otros los usan):

- **C1, registrar un evento (#27)**, unido a más tardar el **martes 10**.
- **C4, pagos vigentes (#53)**, unido a más tardar el **jueves 12**.

---

## Parte 1. Preparar el PC (una vez, hoy)

1. Actualiza tu copia: `git switch main` y `git pull`.
2. Instala OpenSpec (requiere Node.js 22.12 o superior):

```bash
npm install -g @fission-ai/openspec@1.16.0
```
```bash
openspec config set telemetry.enabled false
```

3. Genera los comandos de OpenSpec para Claude Code (no están en el repositorio):

```bash
openspec init --tools claude --no-animation --no-copilot-cloud
```

4. Comprueba: `openspec list --specs` debe mostrar 10 specs y `python manage.py test apps` debe pasar completo.
5. Lee [CONTRIBUTING.md](../../CONTRIBUTING.md), secciones 6 a 8, y la sección de tus Issues en el plan general.

---

## Parte 2. Tus tareas, en orden

| # | Issue | MoSCoW | Unir a más tardar | Depende de | Nivel |
|---|---|---|---|---|---|
| 1 | [#27](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/27) Auditoría: núcleo `registrar()` (**contrato C1**, PR que dice `Refs #27`) | Must | **Mar 10** | #62 de Walther (lun 9) | A |
| 2 | [#53](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/53) Anular un pago (**contrato C4**) | Must | **Jue 12** | C1 | A |
| 3 | [#27](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/27) Auditoría: vista y eventos de pagos e incidentes (`Closes #27`) | Must | Dom 15 | C1 | B |
| 4 | [#6](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/6) Aviso de cobro en PDF | Must | Mié 18 | #62 (PDF y vencimiento), C2 de Maximiliano (mié 11) | A |
| 5 | [#56](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/56) Comprobante de pago | Should | Vie 20 | #62, C2, C4 | B |
| 6 | [#55](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/55) Rendición mensual al comité | Should | Lun 23 | C4, C5 de Walther (mié 18) | A |
| 7 | [#26](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/26) PWA sin conexión | Should | Mar 24 | — | B |
| 8 | [#59](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/59) Prueba guiada (con el equipo) | Should | Mié 25 – jue 26 | Todo lo anterior | C |

Tus dos contratos van primero porque los demás los usan desde la semana 1: C1 lo necesitan los tres para
registrar eventos, y C4 cambia cómo se calcula lo pagado en la cuenta, la cobranza y los reportes. Si a mitad
de la semana 2 vas atrasado, #26 es lo primero que se corta.

Calendario sugerido (unas 15 h por semana):

| Días | Trabajo |
|---|---|
| Sáb 7 – dom 8 | Propuesta de #27 completa (núcleo, vista y eventos) |
| Lun 9 – mar 10 | Cuando #62 esté en `main`: implementar y unir el núcleo C1 |
| Mié 11 – jue 12 | #53 (C4) |
| Vie 13 – dom 15 | #27: vista de auditoría y eventos de pagos e incidentes |
| Lun 16 – mié 18 | #6 |
| Jue 19 – vie 20 | #56 |
| Sáb 21 – lun 23 | #55 (C5 llega el miércoles 18) |
| Mar 24 | #26. **Congelamiento martes 24, 23:59** |
| Mié 25 – jue 26 | #59, correcciones y ensayo |

---

## Parte 3. Modelos y esfuerzo

Trabajas con **Claude Code**. Cada tarea tiene un nivel según su riesgo, y cada fase (proponer, implementar,
archivar) usa un modelo y un esfuerzo distintos:

| Nivel | Cuándo | Proponer (`/opsx:propose`) | Implementar (`/opsx:apply`) | Antes de unir |
|---|---|---|---|---|
| **A** | Contratos, dinero, permisos, seguridad o datos personales, migraciones que tocan datos existentes | `opus` · `high` | `opus` · `high` | `/code-review high` con `opus` |
| **B** | Funcionalidad nueva bien especificada que sigue un patrón que ya existe | `sonnet` · `high` | `sonnet` · `medium` | Revisión propia del diff |
| **C** | Tareas mecánicas: textos, datos demo, archivar, mensajes de commit, ordenar resultados | — | `sonnet` · `low` o `haiku` · `low` | — |

| Fase de OpenSpec | Modelo y esfuerzo |
|---|---|
| `/opsx:explore` (pensar antes de proponer, dudas de diseño) | `opus` · `high` |
| `/opsx:archive` | `sonnet` · `low` |
| Atascado: el mismo problema falla dos veces con Opus | Escalar a `fable` · `xhigh`, solo para ese problema |

**Cómo elegirlos.** Abre Claude Code en la carpeta del proyecto con el modelo y el esfuerzo de la fase:

```bash
claude --model opus --effort high
```

Para cambiar de fase, cierra la sesión y abre otra con los nuevos valores (o usa `/model` para cambiar de
modelo dentro de la sesión). Entre proponer e implementar usa `/clear`: OpenSpec funciona mejor con el contexto
limpio, porque todo lo necesario queda escrito en la propuesta.

**Costo relativo** (precio de la API por millón de tokens de salida, como referencia del consumo de tu plan):
Haiku 5.5 $0,50 · Sonnet 5.5 $10 · Opus 5.5 $20 · Fable 5.1 $50. Por eso Opus se reserva para el nivel A y Fable
solo para desatascarte. Si tu plan no ofrece Fable, escala a `opus` · `xhigh`.

**Por qué estos niveles.** Tus tareas son las que más tocan dinero: un error en C4, en el aviso de cobro o en la
rendición hace que los totales dejen de cuadrar en todo el sistema, y eso es justo lo que el comité revisaría en
la demo. En el nivel B el patrón ya existe en el código, así que Sonnet lo sigue bien con menos consumo. Como
desde el 6 de noviembre la revisión de un compañero no es obligatoria, `/code-review high` en el nivel A
reemplaza esa segunda mirada.

### Modelo y esfuerzo por tarea

| Issue | Proponer | Implementar | Nota |
|---|---|---|---|
| #27 núcleo (C1) | `opus` · `high` | `opus` · `high` | La propuesta cubre todo #27; este PR entrega solo el modelo y `registrar()` |
| #53 Anular pagos (C4) | `opus` · `high` | `opus` · `high` | El cobro recalcula su estado; reportes y cuenta ignoran los anulados |
| #27 vista y eventos | — (mismo cambio de OpenSpec) | `sonnet` · `medium` | Vista de solo lectura, filtrable |
| #6 Aviso de cobro | `opus` · `high` | `opus` · `high` | La suma del aviso debe cuadrar con el cobro y con Mi cuenta |
| #56 Comprobante | `sonnet` · `high` | `sonnet` · `medium` | Reutiliza `renderizar_pdf` de #62 |
| #55 Rendición | `opus` · `high` | `sonnet` · `high` | Los totales cuadran con el reporte y los avisos |
| #26 PWA sin conexión | `sonnet` · `high` | `sonnet` · `medium` | Ver la advertencia de la parte 6 |
| #59 Prueba guiada | — | `sonnet` · `medium` | Para analizar Lighthouse/axe y redactar el informe |

---

## Parte 4. Flujo por Issue (un Pull Request)

1. **Rama nueva desde `main` actualizado:**

```bash
git switch main
```
```bash
git pull
```
```bash
git switch -c feature/27-auditoria-nucleo
```

2. **Proponer** (modelo y esfuerzo de la tabla). En Claude Code escribe `/opsx:propose agregar-registro-de-auditoria`
   (el nombre del cambio está en la sección OpenSpec del Issue) y pega el **prompt de arranque** de la parte 5
   con el número del Issue. Revisa la propuesta y valida:

```bash
openspec validate agregar-registro-de-auditoria --strict
```

3. **Publicar la propuesta:** `git push -u origin feature/27-auditoria-nucleo`, abre el PR como **borrador**
   (`Refs #27` en los PR parciales, `Closes #27` en el último) y avisa en el grupo. Como C1 y C4 son contratos,
   espera un comentario de Walther o Maximiliano sobre las firmas antes de implementar.
4. **Implementar:** `/clear`, cambia al modelo de implementación y escribe `/opsx:apply`. Revisa cada tarea de
   `tasks.md` a medida que avanza.
5. **Verificar:** `python manage.py makemigrations --check`, `python manage.py test apps` y
   `openspec validate --all --strict`. En el nivel A, pide `/code-review high` con `opus`.
6. **Archivar:** `/opsx:archive` con `sonnet` · `low`, en el PR que cierra el Issue.
7. **Unir:** actualiza la rama (`git fetch origin` y `git merge origin/main`), repite el paso 5, haz push,
   marca el PR como listo, espera la CI en verde, **Squash and merge**, borra la rama y avisa en el grupo:
   "Uní #27 (C1); ya pueden usar `registrar()`".

---

## Parte 5. Prompt de arranque para tu agente

Pégalo al empezar cada Issue, cambiando el número:

```text
Eres el agente de Winderson Castrillo en CondoHub (Django 5.2, MySQL 8, en español de Chile).
Vamos a trabajar el Issue #27. Antes de escribir nada, lee:
- el Issue (gh issue view 27 --repo Trinity-Codex/Proyecto_CondoHub, o el texto que te pego),
- docs/equipo/PLAN_PMV_27NOV.md (dueños de carpetas, contratos y reglas de unión),
- CONTRIBUTING.md, secciones 6 a 8, y openspec/config.yaml,
- las specs de openspec/specs/ que el Issue nombra.

Reglas:
1. Solo modificas mis carpetas: apps/pagos, apps/proveedores, apps/incidentes, apps/auditoria,
   apps/rendicion y el service worker en static/. Si necesitas cambiar otro archivo, detente y dime cuál y
   por qué. Excepciones ya acordadas: en #53, una línea en anotar_pagado de apps/gastos/reportes.py para usar
   Pago.objects.vigentes(); en #26, una línea en templates/base.html para registrar el service worker.
2. No cambies config/settings.py, config/urls.py ni requirements.txt.
3. Respeta las firmas de los contratos del plan (C0 a C5). Los míos son
   apps.auditoria.servicios.registrar(usuario, condominio, accion, objeto, antes=None, despues=None) y
   Pago.objects.vigentes().
4. Migraciones: solo en mis apps, una por PR; nunca edites una migración ya unida a main.
5. Toda vista nueva usa RolRequeridoMixin y CondominioQuerysetMixin. Cada criterio de aceptación lleva prueba.
6. Los montos son pesos chilenos enteros: toda suma que muestres (aviso, comprobante, rendición) debe cuadrar
   con Mi cuenta y con el reporte de morosidad, y lleva una prueba que lo verifique.
7. Si el cambio toca dinero o datos personales, registra el evento con apps.auditoria.servicios.registrar.
8. Para los PDF usa apps.core.pdf.renderizar_pdf (de #62); no agregues otra librería.
9. Datos demo solo en el demo.py de mis apps.
10. Nunca escribas claves ni tokens en el código; van en variables de entorno.
11. No hagas push a main, ni force push, ni unas el PR: eso lo hago yo. Pregúntame antes de cualquier comando
    que borre datos o archivos.
12. Al terminar cada tarea de tasks.md, dime qué cambió y qué pruebas corriste.
```

---

## Parte 6. Si algo se complica

| Situación | Qué hacer |
|---|---|
| #62 no está en `main` el lunes en la noche | Avisa a Walther: sin él no existe `apps/auditoria`. Mientras, deja lista la propuesta y las pruebas de C1 |
| C2 o C5 no están en `main` cuando los necesitas | Avanza con plantillas y pruebas, usa un valor provisional en tu rama y avisa en el grupo |
| #26: el service worker se sirve desde `static/` | Desde esa ruta solo controla `/static/`. Para controlar todo el sitio necesita una ruta en la raíz (por ejemplo `/sw.js`), que va en `apps/core/urls.py`, un archivo de Walther: pídesela antes de implementar |
| Conflicto al actualizar con `main` en un archivo que no es tuyo | No lo resuelvas solo: avisa al dueño |
| `main` queda en rojo después de tu unión | Arreglarlo es tu prioridad |
| Bloqueado más de 30 minutos | Avisa en el grupo |
| Vas atrasado el miércoles 18 | Dilo en la reunión diaria: se corta #26 |
