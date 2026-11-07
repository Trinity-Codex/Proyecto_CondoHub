# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver la spec de este cambio.

Estado actual que condiciona el diseño:

- El sitio inicia sesión con `LoginView` y `FormularioInicioSesion` (`AuthenticationForm`). `/admin/` usa otro formulario, `AdminAuthenticationForm`, que también comprueba contraseñas: limitar solo el primero dejaría una puerta abierta.
- `CACHES` no está configurado, así que Django usa una caché en memoria por proceso.
- `apps/cuentas` es carpeta propia. `config/settings.py` es de Walther y no se modifica, por lo que no se puede agregar un `AUTHENTICATION_BACKENDS`.

## Goals / Non-Goals

**Goals:**

- Limitar a 5 intentos cada 15 minutos por correo y por dirección, en toda puerta de ingreso con contraseña.
- Una sola implementación, probada con tiempo simulado.

**Non-Goals:**

- Frenar ataques distribuidos desde muchas direcciones contra correos distintos.
- Registrar intentos más allá de la ventana (la auditoría es otro PR).

## Decisions

### D1. Guardar los intentos en la base de datos

Modelo `IntentoFallido(correo, direccion, creado)` con índices por `correo`+`creado` y `direccion`+`creado`. `creado` usa `default=timezone.now`, lo que permite simular el tiempo en las pruebas.

- **Alternativa descartada, caché:** en memoria cada proceso cuenta por separado, y con varios procesos en producción el límite se multiplica. Una caché compartida exigiría cambiar `settings.py`.
- **Alternativa descartada, `django-axes`:** exige agregar librería, backend y middleware en archivos de Walther, para un caso de pocas líneas.

### D2. Lógica en `apps/cuentas/limite_intentos.py`

Funciones `esta_bloqueado(correo, direccion)`, `registrar_fallo(correo, direccion)` y `limpiar_correo(correo)`, más `direccion_cliente(request)`. Constantes `MAX_INTENTOS = 5` y `VENTANA = 15 minutos`. El correo se normaliza (sin espacios, en minúsculas) para que variar las mayúsculas no evite el límite.

### D3. Un mixin aplicado a los dos formularios

`LimiteIntentosMixin.clean()`:

1. Si ya está bloqueado, muestra el mensaje de bloqueo sin comprobar la contraseña.
2. Llama a `super().clean()`.
3. Si falla, registra el intento. Si con ese intento se llega al límite, muestra de inmediato el mensaje de bloqueo.
4. Si funciona, limpia los intentos del correo.

Se aplica a `FormularioInicioSesion` y a un nuevo formulario de administración, conectado con `admin.site.login_form` en `apps/cuentas/admin.py`.

- **Alternativa descartada, backend de autenticación:** cubriría todo, pero requiere cambiar `settings.py`.

### D4. Ventana deslizante

Hay bloqueo si existen 5 o más intentos dentro de los últimos 15 minutos. Los intentos durante el bloqueo no se registran, así que no lo alargan. El mensaje dice "hasta 15 minutos", porque si los fallos fueron espaciados termina antes.

Mensaje único, sin mencionar la causa: "Demasiados intentos. Espera hasta 15 minutos o usa «¿Olvidaste tu contraseña?» para crear una nueva."

### D5. Qué borra los intentos

Ingresar correctamente y definir una contraseña nueva (`FormularioNuevaClave.save()`) borran las filas **de ese correo**, y así también descuentan de su dirección. No borran las filas de otros correos de esa dirección: de lo contrario, un atacante con cuenta propia podría reiniciar el contador ingresando con ella entre intentos contra otras cuentas. Por lo mismo, recuperar la contraseña no libera una dirección que llegó al límite con otros correos: desde ahí hay que esperar.

### D6. La dirección real del cliente

`direccion_cliente(request)` lee `getattr(settings, "CUENTAS_PROXIES_CONFIABLES", 0)`:

- Con `0` (por defecto) usa `REMOTE_ADDR`.
- Con `n` toma de `X-Forwarded-For` la dirección número `n` contando desde la derecha.

Nunca confía en la cabecera sin esa configuración, porque el visitante podría falsificarla para evitar el límite.

### D7. Los datos duran poco

Cada fallo, ingreso correcto o contraseña nueva elimina las filas fuera de la ventana, con un índice por `creado` para no recorrer la tabla. No se necesita una tarea programada. En el peor caso, las filas quedan hasta el siguiente ingreso o fallo en todo el sitio.

### D8. Spec de RUT

La spec se ajusta a lo que hace el código. `/admin/` sigue aceptando RUT duplicados y la base de datos no lo impide: solo el superusuario llega ahí, y exigir unicidad en la base requiere revisar los RUT vacíos. Queda fuera de este cambio.

## Risks / Trade-offs

- [Detrás de un proxy, todas las visitas comparten dirección y 5 fallos bloquean a todo el sitio] → Walther define `CUENTAS_PROXIES_CONFIABLES` en #29; se avisa en el PR. Es lo más importante de coordinar antes de publicar.
- [Una red compartida, como el wifi de un condominio, se bloquea en conjunto si alguien falla 5 veces] → aceptado porque el Issue pide límite por dirección; dura hasta 15 minutos.
- [Alguien puede bloquear a propósito a otra persona fallando con su correo] → aceptado: es temporal y la persona se desbloquea recuperando su contraseña.
- [Solicitudes simultáneas pueden superar en poco los 5 intentos, porque se cuenta antes de comprobar] → aceptado: un bloqueo de fila por intento no se justifica y el exceso queda limitado a una ráfaga.
- [Se guarda correo e IP de quien falla] → duran como máximo hasta el siguiente ingreso o fallo tras la ventana; #51 debe mencionarlo.
- [El mensaje en `/admin/` menciona un enlace que solo existe en el inicio de sesión del sitio] → aceptado: solo afecta al superusuario.
- [Una dirección IPv6 distinta por intento evita el límite por dirección] → aceptado para el PMV: el límite por correo sigue protegiendo cada cuenta.
- [Cambiar la contraseña en Mi perfil permite probar la clave actual sin límite] → fuera de este cambio: requiere una sesión ya abierta.

## Migration Plan

Agrega una tabla nueva sin tocar datos existentes (`cuentas.0003`). Para revertir: `python manage.py migrate cuentas 0002`.
