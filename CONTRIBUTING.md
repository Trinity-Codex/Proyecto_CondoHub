# Cómo trabajamos en CondoHub

Guía del flujo de trabajo del equipo (Walther, Maximiliano y Winderson). La regla principal:
**`main` siempre funciona**. Nadie sube cambios directo a `main`: todo entra por Pull Request.

## 1. Tomar una tarea

1. Abre el tablero del proyecto (pestaña **Projects** de la organización Trinity-Codex).
2. Elige un Issue de la columna **Todo**, asígnatelo (*Assignees → tú*) y muévelo a **In Progress**.
3. Lee los **criterios de aceptación** del Issue: son la definición de "terminado".

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

- Cada PR necesita la **aprobación de un compañero** y las **pruebas automáticas (CI) en verde**.
- **Quién revisa a quién** (al abrir el PR, elígelo en *Reviewers*):

  | Quien abre el PR | Lo revisa |
  |---|---|
  | Walther | Maximiliano |
  | Maximiliano | Winderson |
  | Winderson | Walther |

  GitHub no permite aprobar el PR propio. Si el revisor asignado no está disponible, puede aprobar el otro compañero.
- Quien revisa: descarga la rama, la prueba y comenta con respeto y de forma concreta.
- Quien recibe comentarios: corrige en la misma rama y vuelve a hacer push (el PR se actualiza solo).

## 6. Unir a main

Con la aprobación y el CI en verde, el autor presiona **Squash and merge** y borra la rama.
Después, todos actualizan su copia:

```bash
git checkout main
git pull
```

## Convenciones del código

- Código, comentarios e interfaz **en español** (modelos `Unidad`, `GastoComun`, etc.).
- Cada vista nueva usa `RolRequeridoMixin` (quién puede entrar) y `CondominioQuerysetMixin`
  (solo datos del condominio activo). Ver `apps/core/permisos.py`.
- Cada modelo nuevo que pertenezca a un condominio debe tener un campo `condominio`
  (o llegar a él, como `Reserva → espacio → condominio`).
- Toda funcionalidad nueva lleva pruebas en el `tests.py` de su app. `apps/core/pruebas.py`
  tiene `crear_escenario()` con datos listos para usar.
- Comenta el código pensando en que lo leerá un compañero que no lo escribió.
