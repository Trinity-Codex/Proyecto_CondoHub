# Proposal

Closes #52 · MoSCoW: **Must** · Hito PMV 27-nov.

## Why

Hoy cualquiera puede probar claves sin límite, y con el sitio publicado (#29) ese riesgo es real (NTI-09, RNF02). El bloqueo debe ser temporal, para no dejar fuera a un adulto mayor que se equivoca, y no debe revelar si un correo tiene cuenta.

## What Changes

- Tras 5 intentos fallidos en 15 minutos con el mismo correo o desde la misma dirección, el ingreso se bloquea temporalmente, incluso con la clave correcta.
- El mensaje es igual exista o no el correo, e indica cómo recuperar la contraseña.
- El bloqueo termina solo cuando los intentos salen de la ventana de 15 minutos.
- Ingresar correctamente o definir una contraseña nueva por el enlace del correo borra los intentos de esa cuenta.
- El límite también cubre el acceso a `/admin/`.
- Los intentos se guardan solo mientras sirven: los antiguos se eliminan.
- La spec de cuentas se corrige según las observaciones del #49: la clave inicial del alta y el alcance real del RUT único.

**Fuera del alcance:**
- Captcha, verificación en dos pasos y aviso por correo del bloqueo.
- Desbloqueo manual por el administrador.
- Eventos de auditoría (PR propio, `Refs #27`).
- Bloquear RUT duplicados en `/admin/`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `cuentas`: «Inicio de sesión con correo» agrega el límite de intentos; «Alta de usuarios por invitación» y «RUT validado» se corrigen para describir lo que hace el código.

## Impact

- **Mis carpetas:** `apps/cuentas` (modelo y migración, `limite_intentos.py`, formularios, `admin.py`, pruebas).
- **Sin librerías nuevas** ni cambios en `config/`, `templates/base.html` o `requirements.txt`.
- **Coordinación con #29 (Walther):** detrás de un proxy, todas las visitas parecen venir de la misma dirección y un solo atacante bloquearía a todo el sitio. Hay que definir `CUENTAS_PROXIES_CONFIABLES` en producción.
- **Datos personales:** guarda correo e IP de cada fallo hasta el primer ingreso o fallo posterior a los 15 minutos; #51 debe mencionarlo en el aviso de privacidad.
- **Datos demo:** no se necesitan.
