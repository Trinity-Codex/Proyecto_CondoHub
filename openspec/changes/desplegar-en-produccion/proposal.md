# Proposal

Closes #29 · MoSCoW: **Must** (hito PMV 27-nov) · URL pública el miércoles 11 de noviembre.

## Why

La evaluación del 27 de noviembre se hace con CondoHub publicado en internet, con HTTPS. Hoy `settings.py` solo
sirve para desarrollo: `DEBUG` encendido por defecto, sin cookies seguras ni estáticos para producción, y el límite
de intentos de la #52 no reconoce al visitante real detrás del proxy del servicio.

## What Changes

- **Servicio:** comparación de tres opciones en `design.md` (decisión 1). Se recomienda Azure for Students; elige
  Walther.
- **Producción por variables de entorno:** `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, base de
  datos con TLS, correo SMTP, HTTPS detrás del proxy, cookies seguras y HSTS, de modo que
  `python manage.py check --deploy` no muestre advertencias. Sin `SECRET_KEY`, la aplicación no arranca en
  producción.
- **Límite de intentos detrás del proxy:** `CUENTAS_PROXIES_CONFIABLES` se lee de una variable de entorno, y la
  dirección que reenvía el proxy se limpia del puerto. Así, cinco fallos de una persona no bloquean a otra.
- **Estáticos y PDF:** WhiteNoise y gunicorn, con versiones exactas. `collectstatic` en cada despliegue y el PDF
  de prueba con su logo funcionando.
- **Arranque:** un script en `config/` migra, recolecta los estáticos, carga la demo solo si no existe, cambia la
  clave demo por una privada y levanta gunicorn. GitHub Actions despliega al unir a `main`, tras la CI.
- **Documentación:** `DOCUMENTACION.md` (sección de despliegue), `.env.example` con valores falsos y la URL
  pública en el `README.md`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: se agregan «Operación en producción», «Límite de intentos detrás del proxy» y «Demo pública con
  clave privada».

## Impact

- Código: `config/settings.py`, `config/entorno.py` (nuevo), `config/arranque_produccion.sh` (nuevo),
  `apps/core` (middleware y comando `clave_demo`, pruebas en `apps/core/tests_produccion.py`), `requirements.txt`,
  `.github/workflows/` (paso `check --deploy` en la CI y `desplegar.yml`).
- Archivos de la raíz que pide el Issue: `.env.example`, `README.md` y `DOCUMENTACION.md`.
- No toca `apps/cuentas`: `limite_intentos.py` sigue igual y recibe la dirección ya limpia.
- Servicio externo: lo configura Walther, con los pasos del PR.

## Fuera del alcance

- Respaldo y restauración de la base (#50).
- Dominio propio, Cloudflare y más de una instancia: la URL del servicio basta para el PMV.
- Reiniciar la demo cada noche: se usa una clave privada en su lugar.
- Monitoreo y alertas más allá del registro del servicio.
