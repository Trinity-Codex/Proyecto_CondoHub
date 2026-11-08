# Maximiliano Soto — Plan de trabajo del PMV (7 al 27 de noviembre)

Plan general del equipo: [PLAN_PMV_27NOV.md](PLAN_PMV_27NOV.md). Este documento es tu hoja de ruta y la de tu
agente de IA: qué haces, en qué orden, con qué modelo y con cuánto esfuerzo.

**Tus carpetas** (solo tú las modificas durante el PMV): `apps/cuentas`, `apps/condominios`,
`apps/comunicados`, `apps/notificaciones`, `apps/reservas`, `apps/privacidad` (la crea #62) y el panel de inicio
(`InicioView` en `apps/core/views.py` y `apps/core/templates/core/inicio.html`).

**Tu contrato** (otros lo usan): **C2, filtro de residencia (#46)**, unido a más tardar el **miércoles 11**.

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
| 1 | [#46](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/46) Fechas de residencia (**contrato C2**) | Must | **Mié 11** | — | A |
| 2 | [#52](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/52) Límite de intentos de inicio de sesión | Must | Mar 10 | — | A |
| 3 | Eventos de auditoría de cuentas y condominios (PR que dice `Refs #27`) | Must | Vie 13 | C1 de Winderson (mar 10) | B |
| 4 | [#51](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/51) Aviso de privacidad y solicitudes del titular | Must | Dom 15 | #62 de Walther (lun 9) | A |
| 5 | [#13](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/13) Importar unidades y residentes | Should | Jue 19 | C2 (tuyo) | A |
| 6 | [#57](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/57) Recordatorios de pago e indicadores | Should | Sáb 21 | #62 (vencimiento), C2 | B |
| 7 | [#58](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/58) Comunicados: vigencia y lectura | Should | Mar 24 | — | B |
| 8 | [#59](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/59) Prueba guiada (con el equipo) | Should | Mié 25 – jue 26 | Todo lo anterior | C |

Empieza **hoy mismo con #46**: es tu contrato y Winderson lo necesita para el aviso de cobro y el comprobante.
#52 es corto y puedes hacerlo en paralelo en otra rama. Si a mitad de la semana 2 vas atrasado, #58 es lo
primero que se corta.

Calendario sugerido (unas 15 h por semana):

| Días | Trabajo |
|---|---|
| Sáb 7 – lun 9 | #46 (propuesta e implementación) y #52 |
| Mar 10 – mié 11 | Terminar y unir #46 (C2) y #52 |
| Jue 12 – vie 13 | Eventos de auditoría de cuentas y condominios |
| Sáb 14 – dom 15 | #51 |
| Lun 16 – jue 19 | #13 |
| Vie 20 – sáb 21 | #57 |
| Dom 22 – mar 24 | #58. **Congelamiento martes 24, 23:59** |
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

**Por qué estos niveles.** En el nivel A un error cuesta caro y lo pagan otros: el filtro de #46 lo usan tres
Issues, y #52 y #51 protegen cuentas y datos personales. En el nivel B el patrón ya existe en el código
(`apps/comunicados` es el módulo de referencia), así que Sonnet lo sigue bien con menos consumo. Como desde el
6 de noviembre la revisión de un compañero no es obligatoria, `/code-review high` en el nivel A reemplaza esa segunda
mirada.

### Modelo y esfuerzo por tarea

| Issue | Proponer | Implementar | Nota |
|---|---|---|---|
| #46 Fechas de residencia | `opus` · `high` | `opus` · `high` | Migración con datos existentes y función que usan otros |
| #52 Límite de intentos | `opus` · `high` | `opus` · `high` | Seguridad: el bloqueo es temporal y el mensaje no revela si el correo existe |
| Eventos de auditoría | — (dentro de tus PR, sin cambio propio) | `sonnet` · `medium` | Solo llamas a `registrar()` de C1 |
| #51 Aviso de privacidad | `opus` · `high` | `sonnet` · `high` | La propuesta define qué datos y derechos cubre (Ley 21.719) |
| #13 Importar unidades | `opus` · `high` | `sonnet` · `high` | Transacción completa, reimportar sin duplicar |
| #57 Recordatorios e indicadores | `sonnet` · `high` | `sonnet` · `medium` | Pruebas con fechas simuladas |
| #58 Comunicados | `sonnet` · `high` | `sonnet` · `medium` | Conteo por unidad, no por persona |
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
git switch -c feature/46-fechas-residencia
```

2. **Proponer** (modelo y esfuerzo de la tabla). En Claude Code escribe `/opsx:propose agregar-fechas-de-residencia`
   (el nombre del cambio está en la sección OpenSpec del Issue) y pega el **prompt de arranque** de la parte 5
   con el número del Issue. Revisa la propuesta y valida:

```bash
openspec validate agregar-fechas-de-residencia --strict
```

3. **Publicar la propuesta:** `git push -u origin feature/46-fechas-residencia`, abre el PR como **borrador**
   con `Closes #46` y avisa en el grupo. Si la propuesta toca un contrato o la carpeta de otro, espera su
   comentario.
4. **Implementar:** `/clear`, cambia al modelo de implementación y escribe `/opsx:apply`. Revisa cada tarea de
   `tasks.md` a medida que avanza.
5. **Verificar:** `python manage.py makemigrations --check`, `python manage.py test apps` y
   `openspec validate --all --strict`. En el nivel A, pide `/code-review high` con `opus`.
6. **Archivar:** `/opsx:archive` con `sonnet` · `low`.
7. **Unir:** actualiza la rama (`git fetch origin` y `git merge origin/main`), repite el paso 5, haz push,
   marca el PR como listo, espera la CI en verde, **Squash and merge**, borra la rama y avisa en el grupo:
   "Uní #46; toca X".

---

## Parte 5. Prompt de arranque para tu agente

Pégalo al empezar cada Issue, cambiando el número:

```text
Eres el agente de Maximiliano Soto en CondoHub (Django 5.2, MySQL 8, en español de Chile).
Vamos a trabajar el Issue #46. Antes de escribir nada, lee:
- el Issue (gh issue view 46 --repo Trinity-Codex/Proyecto_CondoHub, o el texto que te pego),
- docs/equipo/PLAN_PMV_27NOV.md (dueños de carpetas, contratos y reglas de unión),
- CONTRIBUTING.md, secciones 6 a 8, y openspec/config.yaml,
- las specs de openspec/specs/ que el Issue nombra.

Reglas:
1. Solo modificas mis carpetas: apps/cuentas, apps/condominios, apps/comunicados, apps/notificaciones,
   apps/reservas, apps/privacidad y el panel de inicio (InicioView y core/inicio.html). Si necesitas cambiar
   otro archivo, detente y dime cuál y por qué. Excepción ya acordada: en #46, una línea en
   apps/pagos/consultas.py para aplicar cobros_visibles.
2. No cambies config/settings.py, config/urls.py, templates/base.html ni requirements.txt.
3. Respeta las firmas de los contratos del plan (C0 a C5). La de mi contrato C2 es
   apps.condominios.residencias.cobros_visibles(cobros, usuario).
4. Migraciones: solo en mis apps, una por PR; nunca edites una migración ya unida a main.
5. Toda vista nueva usa RolRequeridoMixin y CondominioQuerysetMixin. Cada criterio de aceptación lleva prueba.
6. Si el cambio toca roles o datos personales, registra el evento con apps.auditoria.servicios.registrar.
7. Datos demo solo en el demo.py de mi app.
8. Nunca escribas claves ni tokens en el código; van en variables de entorno. Si agregas una librería, fija su
   versión exacta y la de sus dependencias.
9. No hagas push a main, ni force push, ni unas el PR: eso lo hago yo. Pregúntame antes de cualquier comando
   que borre datos o archivos.
10. Al terminar cada tarea de tasks.md, dime qué cambió y qué pruebas corriste.
```

---

## Parte 6. Si algo se complica

| Situación | Qué hacer |
|---|---|
| Un contrato que necesitas no está en `main` | Avanza con lo que no depende de él (plantillas, pruebas) y avisa en el grupo |
| Conflicto al actualizar con `main` en un archivo que no es tuyo | No lo resuelvas solo: avisa al dueño |
| `main` queda en rojo después de tu unión | Arreglarlo es tu prioridad |
| Bloqueado más de 30 minutos | Avisa en el grupo |
| Vas atrasado el miércoles 18 | Dilo en la reunión diaria: se corta #58 |
