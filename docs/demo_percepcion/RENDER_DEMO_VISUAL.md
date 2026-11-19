# Demo visual de CondoHub en Render

La demo publica las pantallas actuales con datos ficticios y navegación según el rol. Es un servicio separado del despliegue PMV (#29). El acceso público usa HTTPS. Los formularios de negocio y la apertura de notificaciones que las marcaría como leídas están bloqueados en el servidor. Entrar, salir y cambiar el condominio activo siguen disponibles.

## Comprobar la imagen localmente

Desde la raíz de una copia de trabajo de la rama revisada:

```sh
docker build -f Dockerfile.render-demo -t condohub-demo-visual:local .
export RENDER_EXTERNAL_HOSTNAME=condohub-local.onrender.com
export DJANGO_SECRET_KEY="$(python3 -c 'from secrets import token_urlsafe; print(token_urlsafe(64))')"
docker run --rm -d --name condohub-demo-visual-local \
  -e DJANGO_SECRET_KEY -e RENDER_EXTERNAL_HOSTNAME \
  -p 127.0.0.1:10000:10000 condohub-demo-visual:local
```

Cuando Gunicorn esté escuchando, el siguiente GET debe devolver 200. El encabezado de protocolo simula el proxy HTTPS de Render solo en esta prueba local.

```sh
curl --fail --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
  -H "Host: $RENDER_EXTERNAL_HOSTNAME" -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:10000/cuentas/iniciar-sesion/
docker exec condohub-demo-visual-local python manage.py check --deploy
docker exec condohub-demo-visual-local python manage.py test apps.core.tests_render_demo
docker exec condohub-demo-visual-local python manage.py preparar_demo_cliente \
  --settings=config.settings_render_demo
docker stop condohub-demo-visual-local
unset DJANGO_SECRET_KEY RENDER_EXTERNAL_HOSTNAME
```

El comando de preparación interactivo lista las cuentas ficticias al cargar por primera vez. El arranque de Render guarda solo una confirmación en los logs. El arranque recolecta estáticos, prepara la SQLite en `.demo_cliente/` y ejecuta Gunicorn en `0.0.0.0:$PORT`. Repetir la preparación conserva los datos. Una instancia nueva reconstruye los ejemplos.

Django puede emitir W005 y W021 porque la demo aplica HSTS al host asignado y deja desactivados los subdominios y la precarga. W009 puede aparecer con una clave de Render de 44 caracteres si el generador entrega 32 bytes aleatorios codificados en Base64. La comprobación de Django usa longitud como aproximación. Para una clave nueva también se puede usar el generador local del ejemplo y pegar su valor directamente en Render.

## Publicar desde el panel de Render

1. El operador entra a Render y conecta GitHub. Si usa `Git Provider`, autoriza el acceso al repositorio `Trinity-Codex/Proyecto_CondoHub`. Para una conexión por URL pública, selecciona `Public Git Repository` y usa la URL del repositorio.
2. En **CondoHub Demo → Demo** crea un **Web Service** llamado `condohub-demo-visual`. Selecciona la rama que contiene el commit revisado. Una vez integrado el PR, usa `main` con ese cambio.
3. Configura **Docker**, tipo de instancia **Free**, **Root Directory** vacío, **Docker Build Context Directory** `.`, **Dockerfile Path** `./Dockerfile.render-demo` y **Docker Command** vacío. Deja **Pre-Deploy Command** vacío. El **Health Check Path** es `/cuentas/iniciar-sesion/`. Si la opción está disponible, deja **Auto-Deploy** en **Off** para desplegar tras revisar el commit.
4. Agrega `DJANGO_SECRET_KEY` desde **Environment Variables** y presiona **Generate**. Mantén el valor en Render. Render define `RENDER_EXTERNAL_HOSTNAME` y `PORT`. El servicio usa `config.settings_render_demo` desde su imagen.
5. Presiona **Deploy web service**. Anota el commit que muestra Deploys y la URL HTTPS asignada. Comprueba el estado del servicio y los logs antes de pasársela a Walther.

`render.yaml` describe el mismo servicio como Blueprint. Usa una sola de las dos vías de alta para tener una sola instancia y una sola URL.

## Validar la URL de revisión

Usa las cuentas en [Usuarios de demostración](../../README.md#usuarios-de-demostración) y el recorrido del [#101](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/101). Los informes de [operación y finanzas](qa-operacion-finanzas.md) y [comunidad y residente](qa-comunidad-residente.md) sirven como referencia. Oculta valores sensibles en las capturas.

| Sesión | Recorrido y comprobación |
|---|---|
| Sin sesión | GET de login por HTTPS, aviso de demo y acceso protegido al panel. |
| Administrador | Panel, unidades, gastos y cobranza, proveedores, comunicados e incidentes. Comprueba un detalle, un filtro y una acción de negocio bloqueada. |
| Residente | Mi cuenta, comunicados, reservas, incidentes y notificaciones. Abrir una notificación muestra el bloqueo y el estado permanece igual. Una URL de gestión restringida devuelve 403 o 404. |
| Usuario con varias membresías | Cambia al otro condominio desde el selector. Verifica que las páginas y detalles quedan limitados al condominio activo. Elige una cuenta habilitada según el recorrido de #101. |

Registra login y logout, rutas y respuestas, CSS, JavaScript, logotipo y fuentes. Toma evidencias del recorrido a 1440 y 375 px. Comprueba ausencia de 500, errores en estáticos y desbordamiento horizontal. Revisa la vigencia de comunicados y reservas al publicar. Prueba un reinicio y una apertura tras al menos 15 minutos sin tráfico. Entrega a Walther la URL, el commit, los roles, la comprobación del bloqueo y la advertencia de espera.

## Actualizar, reconstruir y apagar

- Para actualizar, revisa el nuevo commit y usa **Manual Deploy** en Render. Repite el recorrido básico de roles, aislamiento y bloqueo.
- Para reconstruir, reinicia o redespliega el servicio. El arranque ejecuta el preparador sobre la base disponible y reconstruye los ejemplos cuando el disco está vacío.
- Para apagar el acceso, usa **Suspend Service** en la configuración del servicio. Verifica después el acceso público.
- Render Free suspende servicios tras 15 minutos de inactividad. El siguiente acceso puede tardar aproximadamente un minuto. SQLite y sesiones son temporales. Si se pierde una sesión, vuelve a entrar con una cuenta ficticia.

Referencias de Render: [Web Services](https://render.com/docs/web-services), [Docker](https://render.com/docs/docker) y [limitaciones de Free](https://render.com/docs/free).
