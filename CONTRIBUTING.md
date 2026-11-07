# Cómo trabajamos en CondoHub

Guía del flujo de trabajo del equipo (Walther, Maximiliano y Winderson). La regla principal:
**`main` siempre funciona**. Nadie sube cambios directo a `main`: todo entra por Pull Request.

## 1. Tomar una tarea

1. Abre el tablero del proyecto (pestaña **Projects** de la organización Trinity-Codex).
2. Elige un Issue de la columna **Todo** respetando el orden MoSCoW del hito (primero `moscow: must`,
   luego `moscow: should`; ver la sección 7), asígnatelo (*Assignees → tú*) y muévelo a **In Progress**.
3. Lee los **criterios de aceptación** del Issue: son la definición de "terminado".
4. Lee su sección **OpenSpec**: dice qué spec cambia y el nombre del cambio que debes crear.

## 2. Crear tu rama

Siempre parte desde un `main` actualizado:

```bash
git checkout main
git pull
git checkout -b feature/12-gastos-comunes
```

Nombre de la rama: `tipo/numeroIssue-descripcion-corta`

| Tipo | Para qué |
|---|---|
| `feature/` | Funcionalidad nueva |
| `fix/` | Corrección de un error |
| `docs/` | Solo documentación |
| `test/` | Solo pruebas |

## 3. Trabajar y hacer commits

- Commits pequeños y frecuentes, con mensajes en español que expliquen **qué** y **por qué**:
  `Agrega cálculo de prorrateo por alícuota (RF02)`.
- Antes de cada commit, ejecuta las pruebas: `python manage.py test apps`.
- Si cambias un modelo: `python manage.py makemigrations` y sube también el archivo de migración.
- **Nunca** subas el archivo `.env`, la carpeta `venv/` ni `db.sqlite3` (el `.gitignore` ya los excluye).

## 4. Abrir el Pull Request (PR)

```bash
git push -u origin feature/12-gastos-comunes
```

En GitHub aparecerá el botón **Compare & pull request**. En la descripción:

- Escribe `Closes #12` (el número del Issue): al unir el PR, el Issue se cierra solo.
- Explica qué hiciste y cómo probarlo.
- Adjunta una captura si cambia algo visible.

## 5. Revisión

- Desde el 6 de noviembre de 2026, cada PR necesita las **pruebas automáticas (CI) en verde**; la aprobación de
  un compañero ya no es obligatoria (decisión del equipo para el PMV, ver
  [docs/equipo/PLAN_PMV_27NOV.md](docs/equipo/PLAN_PMV_27NOV.md)).
- **Pide una revisión** (en *Reviewers* o en el grupo) cuando el PR toque un contrato, un archivo compartido
  (`config/`, `templates/base.html`, `requirements.txt`, `.github/`) o una carpeta de otro integrante.
- Quien revisa: descarga la rama, la prueba y comenta con respeto y de forma concreta.
- Quien recibe comentarios: corrige en la misma rama y vuelve a hacer push (el PR se actualiza solo).

## 6. Unir a main

Antes de unir, actualiza tu rama con `main` (`git fetch origin` y `git merge origin/main`) y vuelve a correr
`python manage.py makemigrations --check`, `python manage.py test apps` y `openspec validate --all --strict`:
dos PR que pasan por separado pueden fallar juntos. Con el CI en verde, el autor presiona **Squash and merge**,
borra la rama y avisa en el grupo qué unió. Después, todos actualizan su copia:

```bash
git checkout main
git pull
```

## 7. Priorización con MoSCoW

Cada Issue lleva una etiqueta de prioridad para la entrega en curso (hoy, el hito **PMV 27-nov**):

| Etiqueta | Significado | Regla |
|---|---|---|
| `moscow: must` | Sin esto no hay entrega | Se termina primero; no se negocia |
| `moscow: should` | Importante, con alternativa temporal | Entra al hito; si hay atraso, se corta desde el último del orden acordado |
| `moscow: could` | Deseable | Solo si sobra tiempo; quien lo tome lo agrega al hito |
| `moscow: won't` | Fuera de esta entrega | Queda abierto para una entrega futura; se explica por qué en la defensa |

Los Issues cerrados de la entrega del 10 de octubre conservan la prioridad que les dio el Informe 1.
La prioridad es de una entrega: al planificar la siguiente se vuelve a revisar.

## 8. Especificaciones con OpenSpec

La carpeta [`openspec/`](openspec/) es la fuente de verdad de **qué debe hacer** CondoHub:

- `openspec/specs/<capacidad>/spec.md`: lo que el sistema ya hace, como requisitos (`SHALL`/`MUST`) con
  escenarios `WHEN`/`THEN`. Hay una spec por capacidad, con el mismo nombre que la etiqueta `módulo:` del Issue.
- `openspec/changes/<cambio>/`: un cambio en curso (propuesta, diseño, tareas y diferencias de la spec).
- `openspec/changes/archive/`: los cambios ya terminados.

### Instalar (una vez por PC)

Requiere **Node.js 22.12 o superior** (https://nodejs.org/). En PowerShell:

```bash
npm install -g @fission-ai/openspec@1.16.0
```
```bash
openspec config set telemetry.enabled false
```

Los comandos para Codex (`.agents/`) y GitHub Copilot (`.github/prompts/`, `.github/skills/`) ya están en el
repositorio. Si usas Claude Code, ejecuta este comando en la carpeta del proyecto para generarlos en tu PC (`openspec update` no los crea):

```bash
openspec init --tools claude --no-animation --no-copilot-cloud
```

Genera `.claude/commands/opsx/` y `.claude/skills/openspec-*/`, que el `.gitignore` ya ignora. No modifica los archivos de `.agents/` ni `.github/`.

### Flujo por Issue (un Pull Request)

1. **Proponer:** en tu rama, pide a tu asistente `/opsx:propose <cambio>` (Claude Code), `$openspec-propose`
   (Codex) o `/opsx-propose` (Copilot), con el nombre del cambio que indica el Issue. Revisa que la propuesta
   enlace el Issue y que `openspec validate <cambio> --strict` pase.
2. **Publicar la propuesta:** sube la rama y abre el Pull Request como **borrador** solo con la propuesta, y
   avisa en el grupo. Si la propuesta cambia un contrato o la carpeta de otro integrante, espera su comentario;
   si no, sigue. Así el qué queda a la vista antes de programar.
3. **Implementar:** `/opsx:apply` sigue `tasks.md`. Marca las tareas a medida que las terminas.
4. **Archivar:** antes de unir, `/opsx:archive` mueve el cambio a `archive/` y actualiza las specs. El PR
   queda listo para unir con el CI en verde (sección 6).

Un Issue que no cambia el comportamiento (pruebas de usabilidad, Docker, documentación) no necesita cambio de
OpenSpec: su sección OpenSpec lo indica.

## Convenciones del código

- Código, comentarios e interfaz **en español** (modelos `Unidad`, `GastoComun`, etc.).
- Cada vista nueva usa `RolRequeridoMixin` (quién puede entrar) y `CondominioQuerysetMixin`
  (solo datos del condominio activo). Ver `apps/core/permisos.py`.
- Cada modelo nuevo que pertenezca a un condominio debe tener un campo `condominio`
  (o llegar a él, como `Reserva → espacio → condominio`).
- Toda funcionalidad nueva lleva pruebas en el `tests.py` de su app. `apps/core/pruebas.py`
  tiene `crear_escenario()` con datos listos para usar.
- Comenta el código pensando en que lo leerá un compañero que no lo escribió.
