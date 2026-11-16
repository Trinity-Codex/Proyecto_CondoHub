#!/bin/sh
# Arranque de la demo visual en Render (Issue #111). Se ejecuta en CADA inicio del contenedor:
# el disco de Render Free es efímero, así que estáticos y SQLite se rehacen aquí.
# -e: cualquier error detiene el arranque (Render no publica una demo a medias).
# -u: una variable sin definir también es un error.
set -eu

export DJANGO_SETTINGS_MODULE=config.settings_render_demo

# La configuración valida DJANGO_SECRET_KEY y RENDER_EXTERNAL_HOSTNAME al cargarse:
# si faltan, estos comandos fallan antes de escribir nada.
python manage.py collectstatic --noinput

# Comando existente (#93): solo SQLite dentro de .demo_cliente/, migra y carga los datos
# ficticios sin duplicarlos. Nunca flush ni cargar_demo --reiniciar.
python manage.py preparar_demo_cliente --settings=config.settings_render_demo

# Un worker: poca memoria en Free y una sola escritura a la vez en SQLite (sesiones).
# El contenedor solo recibe tráfico del proxy de Render, que siempre fija X-Forwarded-Proto.
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --access-logfile - \
    --forwarded-allow-ips "*"
