# Design

## Context

`config/settings_demo.py` ya aísla SQLite. `preparar_demo_cliente` valida su ruta antes de crear directorios, aplicar migraciones y ejecutar `cargar_demo`. Render Free requiere reconstruir el entorno al perder el almacenamiento local.

## Goals / Non-Goals

**Goals:** Preparación idempotente, solo lectura en el servidor, navegación por rol y arranque reproducible desde una imagen sin datos locales.

**Non-Goals:** Despliegue PMV, nueva interfaz, migraciones de modelos, cambios de fixtures compartidos, persistencia, servicios externos y datos reales.

## Decisions

- `config/settings_render_demo.py` concentra la configuración pública. Exige un secreto de entorno y el dominio explícito de Render, usa cookies seguras, reconoce HTTPS detrás del proxy y sirve los estáticos recolectados con WhiteNoise. Usa el backend de correo dummy.
- El middleware de demo decide por método y nombre de ruta resuelta después de CSRF. Los únicos POST autorizados son login, logout y cambio de condominio, con sus validaciones existentes. Se revisan las rutas seguras con efectos de escritura y se bloquean en servidor. La interfaz avisa y orienta sin modificar las validaciones de acceso.
- Docker usa Python 3.12 y conserva las dependencias de MySQL. El arranque recolecta estáticos, prepara la SQLite y ejecuta Gunicorn con un worker. El GET del login sirve como comprobación de salud.
- Render Free usa un solo servicio. El operador configura el secreto y despliega el código revisado. La guía documenta las comprobaciones posteriores y el apagado.

## Risks / Trade-offs

- Las sesiones y SQLite pueden perderse. La demo reconstruye sus datos al arrancar y el primer acceso luego de una suspensión puede tardar.
- El carácter seguro de un GET depende de la vista. Se revisan las rutas actuales y se cubren con regresiones los efectos de escritura identificados.
- Las pruebas SQLite verifican la demo. El CI con MySQL sigue verificando el entorno habitual.
