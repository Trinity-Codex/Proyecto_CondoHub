# Winderson Castrillo — Guía de inicio y tareas

¡Bienvenido a CondoHub! Esta guía tiene todo lo que necesitas para preparar tu PC, entender cómo
trabajamos y hacer tus tareas. Plan general del equipo: [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).

**Tu área:** proveedores, estado de cuenta y pagos de los residentes
(apps nuevas `apps/proveedores/` y `apps/pagos/`).

---

## Parte 0. Seguridad de tu cuenta de GitHub (5 minutos)

Tu cuenta aún no tiene **autenticación en dos pasos (2FA)**. Es lo recomendado para trabajar en
un repositorio compartido (y GitHub puede exigirla):

1. Instala en tu celular **Microsoft Authenticator** o **Google Authenticator**.
2. En GitHub: tu foto (arriba a la derecha) → **Settings** → **Password and authentication** →
   **Enable two-factor authentication**.
3. Elige **Authenticator app**, escanea el código QR con la app y escribe el código de 6 dígitos.
4. **Guarda los códigos de recuperación** (descárgalos): sirven si pierdes el celular.

---

## Parte 1. Preparar tu PC (hoy, una sola vez)

### 1.1 Instalar los programas

| Programa | Dónde | Detalle |
|---|---|---|
| **Python 3.12** | https://www.python.org/downloads/ | En el instalador marca **"Add python.exe to PATH"**. Si ya tienes otra versión (3.13, 3.14), no la desinstales: conviven |
| **MySQL Server 8** | https://dev.mysql.com/downloads/installer/ | Instala *MySQL Server* y *MySQL Workbench*. **Anota la clave de `root`** que definas (es solo tuya, no la compartas ni la subas a GitHub) |
| **Git** | https://git-scm.com/ | Opciones por defecto |
| **VS Code** | https://code.visualstudio.com/ | Extensiones: **Python** (Microsoft) y **Django** (Baptiste Darthenay) |

> **¿Tienes XAMPP?** Su MySQL (MariaDB 10.4) **no sirve** para Django 5.2. Instala MySQL 8 y, si XAMPP
> está abierto, **detén su MySQL** (ambos usan el puerto 3306).

Comprueba en PowerShell:

```bash
py -0
```

Debe aparecer una línea con `3.12`. Y en *Servicios de Windows* (`Win + R` → `services.msc`), el
servicio **MySQL80** debe estar "En ejecución".

### 1.2 Configurar Git con tu nombre

Usa el correo de tu cuenta de GitHub (así tus commits quedan a tu nombre):

```bash
git config --global user.name "Winderson Castrillo"
```
```bash
git config --global user.email "tu-correo-de-github@ejemplo.com"
```

### 1.3 Descargar el proyecto

Elige una carpeta (por ejemplo, Documentos) y en PowerShell:

```bash
git clone https://github.com/Trinity-Codex/Proyecto_CondoHub.git
```
```bash
cd Proyecto_CondoHub
```

La primera vez que Git hable con GitHub te abrirá el navegador para iniciar sesión.

### 1.4 Crear la base de datos (una sola vez)

Abre **MySQL Workbench** → conéctate con `root` → *File → Open SQL Script* →
`docs\crear_base_datos.sql` → presiona el **rayo ⚡**. Abajo deben salir todos los mensajes con ✓
verde. Crea la base `condohub` y el usuario `condohub` (clave `condohub_dev`).

Alternativa por consola, desde la carpeta del proyecto (pide la clave de root):

```bash
Get-Content docs\crear_base_datos.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

### 1.5 Levantar el proyecto

Doble clic en **`iniciar.bat`** (en la carpeta del proyecto). Instala todo, crea las tablas, carga
los datos de demostración y abre http://127.0.0.1:8000/.

Entra con `administrador@condohub.cl` y clave `condohub2026`. Prueba también `residente@condohub.cl`
y `comite@condohub.cl` (misma clave) para ver cómo cambia el sitio según el rol.

### 1.6 Comprobar las pruebas

Detén el servidor (`Ctrl + C`) y, en PowerShell, desde la carpeta del proyecto:

```bash
.\venv\Scripts\Activate.ps1
```
```bash
python manage.py test apps
```

Debe terminar con `Ran 51 tests ... OK`. Si PowerShell bloquea la activación, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 1.7 Abrir en VS Code

*File → Open Folder* → carpeta del proyecto. Luego `Ctrl + Shift + P` → **Python: Select
Interpreter** → elige el que dice `venv`.

### 1.8 Lecturas antes de programar (30 minutos)

1. [CONTRIBUTING.md](../../CONTRIBUTING.md): cómo trabajamos con ramas y Pull Requests.
2. [docs/GUIA_NUEVA_FEATURE.md](../GUIA_NUEVA_FEATURE.md): receta para construir un módulo
   (**tu primera tarea, #9, sigue exactamente esa receta**).
3. [DOCUMENTACION.md](../../DOCUMENTACION.md), secciones 3 y 4: arquitectura y permisos por rol.
4. El código de `apps/comunicados/` (módulo de referencia) y `apps/core/permisos.py`.

Si algo de la Parte 1 falla, envía el mensaje de error completo al grupo.

---

## Parte 2. Cómo trabajar cada tarea

Para **cada** Issue:

```bash
git checkout main
```
```bash
git pull
```
```bash
git checkout -b feature/9-proveedores
```

(Cambia el número y el nombre según el Issue.) Programa, prueba y haz commits:

```bash
git add .
```
```bash
git commit -m "Agrega modelo Proveedor con validación de RUT"
```

Antes de abrir el PR, trae lo último de `main` a tu rama y vuelve a correr las pruebas:

```bash
git pull origin main
```
```bash
python manage.py test apps
```

Sube tu rama y abre el Pull Request en GitHub (botón **Compare & pull request**). En la
descripción escribe `Closes #9` y cómo probarlo. En **Reviewers** elige a **Walther**: él revisa
tus PR; tú revisas los de **Maximiliano**.

Si cambias un modelo: `python manage.py makemigrations` y sube también el archivo de migración.

---

## Parte 3. Tus tareas

| Día | Issue | Tarea | Rama sugerida |
|---|---|---|---|
| **Miércoles 7** | [#9](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/9) | Gestión de proveedores | `feature/9-proveedores` |
| **Jueves 8** | [#3](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/3) | Estado de cuenta del residente (RF03) | `feature/3-estado-de-cuenta` |
| **Viernes 9 (mañana)** | [#4](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/4) | Registrar pagos (RF04) | `feature/4-pagos` |
| **Viernes 9 (tarde)** | #9 (cierre) | Conectar el proveedor con los egresos de Walther | `feature/9-proveedor-en-egresos` |
| Sábado 10 | — | Pruebas finales, datos demo de tus módulos y revisiones | — |

Los **criterios de aceptación** de cada tarea están en su Issue: son la definición de "terminado".

### #9 — Gestión de proveedores (miércoles)

**Dónde:** app nueva `apps/proveedores/`. Sigue la [guía de nuevos módulos](../GUIA_NUEVA_FEATURE.md)
paso a paso, cambiando "Mascota" por "Proveedor".

1. Modelo `Proveedor`: `condominio`, `rut` (con `validators=[validar_rut]` de
   `apps/cuentas/validadores.py`), `razon_social`, `rubro`, `contacto`, `telefono`, `correo`, `activo`.
2. Lista para administrador y comité (`roles_permitidos = [ADMINISTRADOR, COMITE]`); crear, editar
   y desactivar solo el administrador.
3. Enlace **"Proveedores"** en el menú (`templates/base.html`) con `{% if es_admin or es_comite %}`.

**Trampa conocida — RUT repetido:** si pones `UniqueConstraint(condominio, rut)` en el modelo,
Django solo la valida en el formulario cuando `condominio` es un campo del formulario. Como el
condominio lo asigna la vista, valida tú en el `clean_rut()` del formulario:
`Proveedor.objects.filter(condominio=..., rut=...).exclude(pk=self.instance.pk).exists()`
(pásale el condominio al formulario como en `ComunicadoForm`).

**Viernes en la tarde — conectar con los egresos:** cuando #1 (de Walther) y #9 estén en `main`,
abre un PR pequeño que agregue a `Egreso` (en `apps/gastos/models.py`):
`proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True)`,
su migración, y el campo en el formulario de egresos (solo proveedores activos del condominio).
Avísale a Walther: es su app.

### #3 — Estado de cuenta del residente (jueves)

**Dónde:** app nueva `apps/pagos/`.

Depende del modelo `DetalleGastoComun` que **Walther sube el jueves temprano**. Su definición
exacta está en el [plan de trabajo](PLAN_DE_TRABAJO.md#contrato-del-modelo-detallegastocomun-walther-lo-crea-winderson-lo-usa):
mientras llega a `main`, puedes avanzar las plantillas y las vistas usando esos nombres.

1. Vista **"Mi estado de cuenta"** (`roles_permitidos = [RESIDENTE]`): por cada unidad del usuario,
   los cobros de los períodos emitidos (`DetalleGastoComun` con `unidad__residentes__usuario=request.user`),
   con monto, fondo de reserva, total y estado, y el **total adeudado** (pendientes + morosos).
2. Detalle de un período: los egresos del condominio y cómo se calculó el monto de la unidad.
3. Tarjeta **"Mi deuda"** en el panel de inicio (`apps/core/views.py` → `InicioView` y
   `apps/core/templates/core/inicio.html`, dentro de `{% if es_residente %}`). Es un archivo
   compartido: cambio pequeño.
4. Enlace **"Mi cuenta"** en el menú, solo para residentes.

**Seguridad:** un residente **solo** ve sus unidades. Prueba que otro residente reciba 404 al
intentar ver un detalle ajeno (mira `apps/incidentes/tests.py`, `test_residente_solo_ve_sus_incidentes`).

### #4 — Registrar pagos (viernes en la mañana)

**Dónde:** `apps/pagos/`. Únelo a `main` **antes del almuerzo**: Walther lo necesita para los reportes (#5).

1. Modelo `Pago`: `detalle` (FK a `gastos.DetalleGastoComun`, `related_name="pagos"`), `fecha`,
   `monto`, `medio` (transferencia, efectivo, cheque, webpay), `observacion`, `registrado_por`.
2. El administrador registra pagos desde el estado de cuenta de una unidad. Se permiten pagos parciales.
3. Al guardar: si la suma de pagos del detalle alcanza su `total`, el detalle pasa a `PAGADO`.
   Usa `transaction.atomic()` y no permitas pagar **más** de lo adeudado.
4. Avisa al residente que su pago fue registrado con el **patrón Observer**: `Pago` hereda de
   `Sujeto` (como `Incidente`) y se suscribe en `apps/notificaciones/apps.py`. Ese archivo es de
   Maximiliano (él agrega el correo en #14): si aparece un conflicto, conserva las dos líneas.

---

## Parte 4. Lista diaria

- [ ] `git checkout main` y `git pull` al empezar el día.
- [ ] `python manage.py migrate` (por si un compañero agregó tablas).
- [ ] Reunión diaria de 15 minutos: qué hice, qué haré, qué me bloquea.
- [ ] Revisar los PR de **Maximiliano** el mismo día.
- [ ] Antes de terminar el día: tu trabajo subido (aunque sea en tu rama) y el Issue movido en el tablero.

## ¿Te bloqueaste?

1. Revisa la sección "Problemas comunes" de [DOCUMENTACION.md](../../DOCUMENTACION.md).
2. Mira cómo se hizo algo parecido en `apps/comunicados/` o `apps/incidentes/`.
3. Si pasan 30 minutos sin avanzar, avisa en el grupo con el mensaje de error completo.
