# Design

## Context

- `config/settings.py` lee del `.env` la clave, `DEBUG` (encendido por defecto), `ALLOWED_HOSTS`, la base MySQL,
  `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL` y `SITIO_URL`. No tiene `STATIC_ROOT`, `CSRF_TRUSTED_ORIGINS`, ajustes de
  HTTPS ni datos SMTP. `.gitignore` ya excluye `staticfiles/` y `.env`.
- `apps/core/pdf.py` (#62) ya busca los estáticos en `STATIC_ROOT`, con los nombres con hash de WhiteNoise. Una
  prueba lo cubre (`test_lee_nombres_con_hash_desde_static_root`).
- `apps/cuentas/limite_intentos.py` (#52, carpeta de Maximiliano) lee `CUENTAS_PROXIES_CONFIABLES` con `getattr`
  (0 por defecto) y toma la dirección n-ésima desde la derecha de `X-Forwarded-For`. Nadie define el ajuste.
- `cargar_demo` no hace nada si los condominios demo existen, y `--reiniciar` los borra. La clave demo
  (`CLAVE_DEMO` en `apps/cuentas/demo.py`) está publicada en el README.
- La CI (`ci.yml`) corre con MySQL 8, `DEBUG` por defecto y `cargar_demo`.

## Goals / Non-Goals

**Goals:** URL pública con HTTPS el miércoles 11, a costo cero, desplegada desde `main` sin pasos a mano después de
la configuración inicial; la misma configuración en desarrollo y producción, con diferencias solo en variables.

**Non-Goals:** contenedores (Docker), más de una instancia, almacenamiento de archivos subidos (CondoHub no tiene
`MEDIA`) y respaldo (#50).

## Decisions

### 1. Servicio: Azure for Students (recomendado); elige Walther

Datos verificados el 7 de noviembre de 2026 en las páginas oficiales.

| | **Azure for Students** | **PythonAnywhere Developer** | **Railway Hobby** |
|---|---|---|---|
| Costo | 0: 100 USD de crédito por 12 meses, sin tarjeta, para estudiantes verificados. App Service B1 ≈ 13 USD/mes (estimación; confirmar en la calculadora) | 10 USD/mes (el plan de 5 USD desapareció en enero de 2026) | 5 USD/mes (el plan gratis da 1 USD/mes, que no alcanza) |
| MySQL 8 | Azure Database for MySQL Flexible Server, B1MS gratis 750 h/mes por 12 meses, 32 GB | Incluido en el plan pagado; las cuentas gratis creadas desde el 15-ene-2026 no tienen MySQL. Versión por confirmar | Plantilla MySQL dentro del proyecto (servicio propio, sin respaldo administrado) |
| HTTPS | Sí, en `*.azurewebsites.net` | Sí, en `*.pythonanywhere.com` | Sí, en `*.up.railway.app` |
| Desde GitHub | GitHub Actions (`azure/webapps-deploy`) | Manual (`git pull` en su consola) o script | Automático al hacer push |
| Correo SMTP | Puerto 587 autenticado permitido en todas las suscripciones | Libre en planes pagados | **Bloqueado en Hobby**: exige una API HTTP (Resend, etc.) y otra librería |
| Duerme / límites | B1 con *Always On*: no duerme. F1 gratis: 60 min de CPU al día y sin *Always On* (no sirve) | No duerme; 5 GB de disco | No duerme; consumo cobrado sobre 5 USD |
| Región | **Chile Central** (Santiago) para MySQL; App Service por confirmar, si no Brazil South | EE. UU. o Europa | EE. UU., Europa o Singapur |

**Por qué Azure:** es el único con costo cero hasta diciembre, base MySQL administrada con respaldo automático
(útil para #50) y región en Chile. **Contras:** más pasos de configuración y la cabecera de reenvío trae el puerto
(decisión 4). **Plan B:** PythonAnywhere Developer, el camino más corto si la verificación de estudiante falla o
el domingo 9 Azure aún no responde. La configuración de este diseño sirve para ambos; solo cambian los valores de
las variables y el arranque.

Fuentes: azure.microsoft.com/free/students, learn.microsoft.com (MySQL Flexible Server: cuenta gratis, regiones y
novedades; límites de App Service; SMTP saliente), pythonanywhere.com/pricing y help.pythonanywhere.com
(FreeAccountsFeatures, KindsOfDatabases), docs.railway.com (pricing/plans, networking/outbound-networking,
deployments/regions).

### 2. Configuración: funciones de lectura en `config/entorno.py`

`settings.py` usa funciones puras (`booleano`, `entero`, `lista`) que reciben el diccionario del entorno; así se
prueban sin recargar los ajustes. Variables (en `.env.example` con valores falsos como `changeme`):

| Variable | Producción (de dónde sale el valor) |
|---|---|
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | Generada por Walther (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_ALLOWED_HOSTS` | Nombre del sitio en el servicio |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` + ese nombre |
| `DJANGO_PROXY_HTTPS` | `1`: confía en `X-Forwarded-Proto` del proxy |
| `DJANGO_HSTS_SEGUNDOS` | `3600` al inicio; se sube cuando todo funcione |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Panel de la base del servicio |
| `DB_SSL` | `1` (Azure exige TLS) |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Proveedor SMTP que elija Walther |
| `SITIO_URL` | `https://` + nombre del sitio |
| `CUENTAS_PROXIES_CONFIABLES` | `1` en Azure (un proxy), `2` si se agrega Cloudflare, `0` sin proxy |
| `DEMO_CLAVE` | Clave privada de las cuentas demo (decisión 7) |

Con `DEBUG` apagado se activan `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS con
subdominios y *preload* (sin inscribir el dominio en la lista: solo evita la advertencia W021), y `LOGGING` envía
los errores a la consola (el registro del servicio). Si la clave falta o empieza con `django-insecure`,
`settings.py` lanza `ImproperlyConfigured`. **Alternativa descartada:** silenciar advertencias de `check --deploy`.

### 3. Base de datos con TLS

Con `DB_SSL=1`, `OPTIONS` agrega `ssl_mode: REQUIRED` (mysqlclient 2.3) y `CONN_MAX_AGE=60` con
`CONN_HEALTH_CHECKS`. Verificar el certificado (`VERIFY_CA`) exigiría versionar el certificado raíz; queda como
mejora.

### 4. Dirección real detrás del proxy

`CUENTAS_PROXIES_CONFIABLES = entero(entorno, "CUENTAS_PROXIES_CONFIABLES", 0)` en `settings.py`. App Service
reenvía `X-Forwarded-For` como `ip:puerto`, y el puerto cambia en cada conexión: sin limpiarlo, cada intento
tendría una dirección distinta y el límite por dirección no funcionaría. Un middleware nuevo en
`apps/core/middleware.py`, antes de `CondominioActivoMiddleware`, quita el puerto de cada elemento (también
`[ipv6]:puerto`) y descarta lo que no sea una IP válida (`ipaddress`). `limite_intentos.py` no cambia.
**Alternativa descartada:** cambiar `direccion_cliente`, que es de Maximiliano y ya está unido.

### 5. Estáticos y servidor

`whitenoise==6.12.0` (sin dependencias) y `gunicorn==26.2.0` (`packaging==26.3`; confirmar con `pip freeze`).
`WhiteNoiseMiddleware` va justo después de `SecurityMiddleware`. `STATIC_ROOT = BASE_DIR / "staticfiles"`; con
`DEBUG` apagado, `STORAGES["staticfiles"]` usa `CompressedManifestStaticFilesStorage`, y en desarrollo y en las
pruebas queda el almacenamiento normal, así no exigen `collectstatic`.

### 6. Arranque y despliegue

`config/arranque_produccion.sh` (comando de inicio de App Service): `migrate --noinput`, `collectstatic --noinput`,
`cargar_demo` (sin `--reiniciar`: no borra nada si la demo existe), `clave_demo` y
`gunicorn config.wsgi --workers 2 --timeout 120`. `.github/workflows/desplegar.yml` se activa con `workflow_run`
cuando la CI termina en verde en `main` (y a mano con `workflow_dispatch`), inicia sesión en Azure con OIDC y
despliega con `azure/webapps-deploy`. No se usa el asistente del Centro de implementación, porque sube su propio
flujo directo a `main`, que está protegida.

### 7. Clave demo privada

Comando nuevo `apps/core/management/commands/clave_demo.py`: asigna `DEMO_CLAVE` a los usuarios de `USUARIOS`
(`apps/cuentas/demo.py`, solo lectura). Con `DEBUG` apagado y sin `DEMO_CLAVE`, falla y el arranque se detiene. Es
idempotente y no toca otras cuentas. **Alternativa descartada:** reiniciar la demo cada noche, que necesita una
tarea programada y borra lo que el docente pruebe.

## Risks / Trade-offs

- [App Service no disponible en Chile Central para la suscripción] → Brazil South para el sitio y la base juntos.
- [Compilar `mysqlclient` en el servidor falla] → registro de compilación de App Service; si falla, se instala
  `default-libmysqlclient-dev` en el arranque o se pasa al plan B.
- [Qué elemento de `X-Forwarded-For` escribe Azure] → probar en la URL pública: 5 fallos desde el celular (otra
  red) y revisar en el admin de Django que `IntentoFallido.direccion` sea la IP del celular, sin puerto.
- [El crédito se agota] → B1 cuesta unos 26 USD de noviembre a diciembre; al agotarse, Azure detiene los recursos
  sin cobrar.
- [HSTS largo mal configurado deja el sitio inaccesible] → 3600 s hasta confirmar HTTPS.

## Migration Plan

Primer despliegue sobre una base vacía: el arranque crea las tablas y la demo. Si una versión falla, se vuelve a
desplegar el commit anterior con `workflow_dispatch`. Las migraciones solo avanzan; la base no se borra.
