# Tasks

## 1. Registro de intentos

- [ ] 1.1 Crear el modelo `IntentoFallido` con sus índices y una sola migración (`cuentas.0003`). Verificar con `makemigrations --check` y con `migrate cuentas 0002` seguido de `migrate` en la base local.
- [ ] 1.2 Crear `apps/cuentas/limite_intentos.py` con `esta_bloqueado`, `registrar_fallo`, `limpiar_correo` y las constantes (D2, D4, D5, D7). Verificar con pruebas en `apps/cuentas/tests.py`: bloqueo por correo y por dirección, normalización de mayúsculas, salida de la ventana con tiempo simulado, y eliminación de filas antiguas.
- [ ] 1.3 Agregar `direccion_cliente(request)` (D6). Verificar con pruebas usando `override_settings`: sin configuración ignora una cabecera `X-Forwarded-For` falsificada; con `CUENTAS_PROXIES_CONFIABLES=1` toma la dirección correcta; sin `REMOTE_ADDR` no falla.

## 2. Inicio de sesión del sitio

- [ ] 2.1 Crear `LimiteIntentosMixin` y aplicarlo a `FormularioInicioSesion` (D3). Verificar con pruebas de inicio de sesión: el quinto fallo muestra el bloqueo, la clave correcta durante el bloqueo no entra y no se abre sesión.
- [ ] 2.2 Probar que el mensaje no revela si el correo existe: la respuesta es idéntica con un correo registrado y con uno inexistente, y lo es también antes del bloqueo.
- [ ] 2.3 Probar el fin del bloqueo: con tiempo simulado, tras salir de la ventana la persona entra sin intervención; los intentos durante el bloqueo no lo alargan.
- [ ] 2.4 Borrar los intentos al ingresar correctamente y en `FormularioNuevaClave.save()` (D5). Verificar con pruebas: el ingreso correcto reinicia el contador, recuperar la contraseña desbloquea de inmediato por el flujo completo del correo, e ingresar con una cuenta propia no borra los intentos contra otra.

## 3. Panel de administración

- [ ] 3.1 Crear el formulario de administración con el mixin y conectarlo con `admin.site.login_form` en `apps/cuentas/admin.py`. Verificar con pruebas: 5 fallos en `/admin/login/` bloquean, el superusuario entra normalmente sin bloqueo, y los fallos en `/admin/` cuentan también para el sitio.

## 4. Verificación de integración

- [ ] 4.1 Probar en el navegador el flujo completo (fallar 5 veces, ver el mensaje y recuperar la contraseña con el enlace de la consola), revisando que se vea bien a 360 px.
- [ ] 4.2 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [ ] 4.3 Ejecutar `/code-review high` con `opus` (nivel A del plan) y corregir lo que corresponda; verificar repitiendo 4.2.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #52` y avisar a Walther que #29 debe definir `CUENTAS_PROXIES_CONFIABLES` si publica detrás de un proxy.
- Archivar con `/opsx:archive` (`sonnet` · `low`) antes de unir.
- Actualizar la rama con `main`, repetir 4.2, marcar el PR como listo y esperar la CI en verde. Maximiliano hace el **Squash and merge** y avisa en el grupo, a más tardar el martes 10.
