# Maximiliano Soto — Guía de inicio y tareas

¡Bienvenido a CondoHub! Esta guía tiene todo lo que necesitas para preparar tu PC, entender cómo
trabajamos y hacer tus tareas. Plan general del equipo: [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).

**Tu área:** administración del condominio y de las cuentas de usuario
(`apps/condominios/`, `apps/cuentas/` y `apps/notificaciones/`).

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
git config --global user.name "Maximiliano Soto"
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
y `conserje@condohub.cl` (misma clave) para ver cómo cambia el sitio según el rol.

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
2. [docs/GUIA_NUEVA_FEATURE.md](../GUIA_NUEVA_FEATURE.md): receta para construir un módulo.
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
git checkout -b feature/10-gestion-unidades
```

(Cambia el número y el nombre según el Issue.) Programa, prueba y haz commits:

```bash
git add .
```
```bash
git commit -m "Agrega formulario para crear unidades (RF01)"
```

Antes de abrir el PR, trae lo último de `main` a tu rama y vuelve a correr las pruebas:

```bash
git pull origin main
```
```bash
python manage.py test apps
```

Sube tu rama y abre el Pull Request en GitHub (botón **Compare & pull request**). En la
descripción escribe `Closes #10` y cómo probarlo. **Walther** revisa tus PR; tú revisas los de
**Winderson**.

Si cambias un modelo: `python manage.py makemigrations` y sube también el archivo de migración.

---

## Parte 3. Tus tareas

| Día | Issue | Tarea | Rama sugerida |
|---|---|---|---|
| **Miércoles 7** | [#10](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/10) | Administrar edificios, unidades y residentes desde el sitio (RF01) | `feature/10-gestion-unidades` |
| **Jueves 8** | [#11](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/11) | Alta de usuarios y recuperación de contraseña (RF12) | `feature/11-alta-usuarios` |
| **Viernes 9** | [#12](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/12) | Perfil de usuario | `feature/12-perfil` |
| **Viernes 9** | [#14](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/14) | Notificaciones por correo (RF10, patrón Observer) | `feature/14-correo` |
| Sábado 10 | — | Pruebas finales, datos demo de tus módulos y revisiones | — |

Los **criterios de aceptación** de cada tarea están en su Issue: son la definición de "terminado".

### #10 — Administrar edificios, unidades y residentes (miércoles)

**Dónde:** `apps/condominios/` (`forms.py` nuevo, `views.py`, `urls.py`, `templates/condominios/`).
Hoy existe la página de consulta `UnidadesView` (`/condominio/unidades/`); agrega allí los botones.

1. Formularios `EdificioForm`, `UnidadForm` (número, piso, tipo, alícuota) y `ResidenteForm`
   (correo del usuario + tipo: propietario/arrendatario/familiar). Hereda de `ModeloFormularioBootstrap`.
2. Vistas crear/editar/eliminar para edificios y unidades, y "agregar residente" / "dar de baja"
   (`activo=False`, no se borra). Todas con `roles_permitidos = [ADMINISTRADOR]`.
3. En `unidades.html`, muestra los botones solo con `{% if es_admin %}`.

**Trampas conocidas:**

- **Números repetidos:** el modelo tiene `UniqueConstraint(edificio, numero)`, pero Django solo la
  valida en el formulario si `edificio` es un campo del formulario. Si el edificio lo pones en la
  vista, valida tú en `clean()`:
  `Unidad.objects.filter(edificio=..., numero=...).exclude(pk=self.instance.pk).exists()`.
- **Agregar residente por correo:** busca con `Usuario.objects.filter(email__iexact=correo).first()`;
  si no existe, muestra un error ("primero crea la cuenta", eso lo resuelve tu #11).
  `Residente.save()` ya le da el rol RESIDENTE solo.
- **Condominio activo:** los edificios que se pueden elegir son solo los de `request.condominio`.

### #11 — Alta de usuarios y recuperación de contraseña (jueves)

**Dónde:** `apps/cuentas/` y `config/settings.py` (configuración de correo).

1. En `config/settings.py` agrega el correo de desarrollo (los correos se imprimen en la consola
   del servidor, no se envían de verdad):
   ```python
   EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
   DEFAULT_FROM_EMAIL = "CondoHub <no-responder@condohub.cl>"
   ```
2. **Recuperar contraseña:** usa las vistas de Django `PasswordResetView`, `PasswordResetDoneView`,
   `PasswordResetConfirmView` y `PasswordResetCompleteView` en `apps/cuentas/urls.py`, con plantillas
   propias en `templates/cuentas/`. Agrega el enlace "¿Olvidaste tu contraseña?" en `iniciar_sesion.html`.
3. **Alta por el administrador:** formulario con correo, nombre, apellido, RUT y rol. La vista crea
   el `Usuario` y su `Membresia` en el condominio activo, y le envía el correo para que defina su clave.

**Trampas conocidas:**

- **Nombres de rutas:** nuestras rutas tienen el prefijo `cuentas:` (por `app_name`). Las vistas de
  Django buscan por defecto rutas sin prefijo (`password_reset_done`). Indica siempre
  `success_url=reverse_lazy("cuentas:...")` y un `email_template_name` propio cuyo enlace use
  `{% url 'cuentas:<tu_ruta_de_confirmacion>' uidb64=uid token=token %}`.
- **El correo de "define tu clave" no llega:** `PasswordResetForm` **ignora** a los usuarios con
  `set_unusable_password()`. Al crear el usuario, dale una clave aleatoria:
  `import secrets` → `usuario.set_password(secrets.token_urlsafe(16))`. Y para enviar el correo,
  reutiliza `PasswordResetForm({"email": usuario.email})` → `is_valid()` → `save(request=request, ...)`.
- `make_random_password()` ya **no existe** en Django 5: usa `secrets`.

### #12 — Perfil de usuario (viernes)

**Dónde:** `apps/cuentas/`.

1. Vista `UpdateView` sobre el propio usuario (`get_object()` devuelve `self.request.user`) con
   nombre, apellido, RUT y teléfono. El correo no se edita.
2. Cambio de contraseña con `PasswordChangeView` (`success_url` con prefijo `cuentas:`).
3. Enlace **"Mi perfil"** en el menú del usuario (`templates/base.html`, dentro del desplegable).

### #14 — Notificaciones por correo (viernes)

**Dónde:** `apps/notificaciones/` (y un campo nuevo en `apps/cuentas/models.py`).

Es la demostración del **patrón Observer** del Informe 2: agregas un canal nuevo **sin tocar**
comunicados ni incidentes.

1. En `apps/notificaciones/observador.py`, crea `NotificadorCorreo(Observador)` cuyo
   `actualizar(evento)` envíe un correo (`django.core.mail.send_mail`) a cada destinatario.
2. Suscríbelo en `apps/notificaciones/apps.py` (una línea por sujeto, como `NotificadorEnSitio`).
3. Agrega al `Usuario` el campo `recibir_correos = models.BooleanField(default=True)`
   (con su migración) y muéstralo en el perfil de #12. El observador solo envía a quien lo tenga activo.
4. Pruebas: Django guarda los correos de las pruebas en `django.core.mail.outbox`.

**Coordinación:** Winderson agregará en el mismo `apps.py` la suscripción de los pagos (#4). Si les
aparece un conflicto ahí, basta con conservar las dos líneas.

---

## Parte 4. Lista diaria

- [ ] `git checkout main` y `git pull` al empezar el día.
- [ ] `python manage.py migrate` (por si un compañero agregó tablas).
- [ ] Reunión diaria de 15 minutos: qué hice, qué haré, qué me bloquea.
- [ ] Revisar los PR de **Winderson** el mismo día.
- [ ] Antes de terminar el día: tu trabajo subido (aunque sea en tu rama) y el Issue movido en el tablero.

## ¿Te bloqueaste?

1. Revisa la sección "Problemas comunes" de [DOCUMENTACION.md](../../DOCUMENTACION.md).
2. Mira cómo se hizo algo parecido en `apps/comunicados/` o `apps/incidentes/`.
3. Si pasan 30 minutos sin avanzar, avisa en el grupo con el mensaje de error completo.
