# Tasks

## 1. Librerías

- [ ] 1.1 Agregar a `requirements.txt` `whitenoise==6.12.0` y `gunicorn==26.2.0` con un comentario, más cada
  dependencia que muestre `pip freeze` tras instalarlas (se espera `packaging==26.3`); verificar que
  `pip install -r requirements.txt` termina en el `venv` de Windows y que `pip check` no reporta conflictos.

## 2. Lectura de variables (`config/entorno.py`)

- [ ] 2.1 Crear `config/entorno.py` con `booleano`, `entero` y `lista`, que reciben el diccionario del entorno
  (decisión 2), y usarlas en `settings.py` en lugar de `_booleano`; verificar con pruebas en
  `apps/core/tests_produccion.py` (valores vacíos, espacios, comas sobrantes, entero inválido) y con
  `python manage.py check`.

## 3. Ajustes de producción en `settings.py`

- [ ] 3.1 Leer `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_PROXY_HTTPS` (`SECURE_PROXY_SSL_HEADER`) y
  `DJANGO_HSTS_SEGUNDOS`, y con `DEBUG` apagado activar redirección a HTTPS, cookies seguras, HSTS con subdominios
  y *preload*; verificar con una prueba que ejecuta `manage.py check --deploy --fail-level WARNING` en un
  subproceso con variables de producción falsas y termina con código 0.
- [ ] 3.2 Con `DEBUG` apagado, lanzar `ImproperlyConfigured` si falta `DJANGO_SECRET_KEY` o empieza con
  `django-insecure`; verificar con una prueba en subproceso que el error nombra la variable.
- [ ] 3.3 Agregar `DB_SSL` (`ssl_mode: REQUIRED`), `CONN_MAX_AGE=60` y `CONN_HEALTH_CHECKS`; verificar con una
  prueba de `entorno` que arma `OPTIONS` con y sin `DB_SSL`, y que la CI sigue conectando sin TLS.
- [ ] 3.4 Leer `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` y
  `EMAIL_TIMEOUT`; verificar con una prueba que los valores del entorno llegan a los ajustes y que sin ellos sigue
  el backend de consola.
- [ ] 3.5 Agregar `LOGGING` que envía los errores a la consola con `DEBUG` apagado; verificar con
  `check --deploy` y revisando el registro del servicio tras un error provocado en 6.4.
- [ ] 3.6 Actualizar `.env.example` con cada variable nueva, comentada y con valores falsos (`changeme`); verificar
  que copiar el archivo como `.env` sigue funcionando en desarrollo (`python manage.py runserver` y la página de
  inicio de sesión).

## 4. Límite de intentos detrás del proxy

- [ ] 4.1 Definir `CUENTAS_PROXIES_CONFIABLES` en `settings.py` con `entero(..., 0)`; verificar con una prueba que
  la variable de entorno llega al ajuste.
- [ ] 4.2 Agregar a `apps/core/middleware.py` el middleware que quita el puerto de cada elemento de
  `X-Forwarded-For` (`ip:puerto` y `[ipv6]:puerto`) y descarta lo que no sea IP, registrado antes de
  `CondominioActivoMiddleware`; verificar con pruebas unitarias de esos formatos.
- [ ] 4.3 Pruebas de los escenarios de «Límite de intentos detrás del proxy» con `CUENTAS_PROXIES_CONFIABLES=1`:
  un residente falla 5 veces y el administrador entra desde otra dirección; 5 fallos con puertos distintos bloquean
  el sexto; una dirección inventada a la izquierda no cambia la registrada. Verificar con
  `python manage.py test apps.core apps.cuentas`.

## 5. Estáticos, demo y arranque

- [ ] 5.1 Agregar `WhiteNoiseMiddleware`, `STATIC_ROOT` y `STORAGES` según la decisión 5; verificar con una prueba
  que, tras `collectstatic` en una carpeta temporal con el almacenamiento con hash, el PDF de prueba
  (`core/pdf/prueba.html`) trae el logo, y que `python manage.py test apps` no muestra advertencias de WhiteNoise.
- [ ] 5.2 Crear el comando `clave_demo` (decisión 7); verificar con pruebas: cambia la clave solo de los usuarios
  demo, la clave del README deja de servir, otra cuenta no cambia, y con `DEBUG` apagado sin `DEMO_CLAVE` falla.
- [ ] 5.3 Pruebas de los escenarios de «Demo pública con clave privada»: `cargar_demo` dos veces más un dato creado
  por un usuario no borra ni duplica nada; con la clave privada el administrador entra a su panel y el residente
  demo recibe 403 en una página del administrador.
- [ ] 5.4 Registrar en auditoría el cambio de clave de `clave_demo` con `apps.auditoria.servicios.registrar` si el
  contrato C1 (#27) ya está en `main`; si no, dejar un comentario `# Pendiente C1 (#27)` y avisar en el PR.
- [ ] 5.5 Crear `config/arranque_produccion.sh` (decisión 6) con `set -e`; verificar en Git Bash con
  `USE_SQLITE=1` y variables falsas que llega a iniciar gunicorn (o, en Windows, hasta el paso anterior).

## 6. CI, despliegue y documentación

- [ ] 6.1 Agregar a `ci.yml` un paso que corre `check --deploy --fail-level WARNING` con `DJANGO_DEBUG=0` y una
  clave generada en el mismo paso; verificar que la CI del PR queda en verde.
- [ ] 6.2 Crear `.github/workflows/desplegar.yml` (decisión 6) con versiones fijas de las acciones y los
  identificadores de Azure como secretos de GitHub; verificar con `workflow_dispatch` desde la rama antes de unir.
- [ ] 6.3 Escribir en `DOCUMENTACION.md` la sección «Despliegue en producción» (servicio, variables, arranque,
  cómo volver a una versión anterior y `CUENTAS_PROXIES_CONFIABLES`) y poner la URL pública en el `README.md`, con
  la nota de que la clave demo pública es otra y se entrega por un canal privado.
- [ ] 6.4 Verificación final en la URL pública: `http://` redirige a `https://`; una URL inexistente muestra la
  página de error sin detalles; inicio de sesión con la clave privada y rechazo de la clave del README; correo de
  recuperación recibido en una bandeja real; PDF de prueba con logo (consola SSH del servicio); 5 fallos desde el
  celular no bloquean otra red y `IntentoFallido.direccion` queda sin puerto; redesplegar sin perder datos.
- [ ] 6.5 Correr `python manage.py test apps` completo, `makemigrations --check` y
  `openspec validate --all --strict`; verificar que todo pasa en Windows y en la CI.

## Workflow follow-up

- Archivar el cambio con `/opsx:archive` en el mismo PR, antes de unirlo, para que la spec `plataforma` quede al día.
- Unir el miércoles 11 con la URL pública funcionando, y avisar en el grupo que cambió `settings.py`.
