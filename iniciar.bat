@echo off
chcp 65001 >nul
title CondoHub
REM Ir a la carpeta donde esta este archivo (la del proyecto).
cd /d "%~dp0"

REM ==========================================================================
REM  Deja CondoHub funcionando con doble clic:
REM    1. busca Python 3.12 (o 3.13 / 3.11) y crea el entorno virtual "venv"
REM    2. instala las librerias de requirements.txt
REM    3. crea el archivo .env (configuracion local) si no existe
REM    4. crea o actualiza las tablas en MySQL (migrate)
REM    5. carga los datos de demostracion (solo la primera vez)
REM    6. levanta el servidor y abre el navegador
REM  Antes, UNA sola vez: ejecutar docs\crear_base_datos.sql en MySQL (ver DOCUMENTACION.md).
REM ==========================================================================
set PYTHONIOENCODING=utf-8

echo [1/6] Preparando Python y el entorno virtual...
if exist venv\Scripts\python.exe goto activar
set PY=
for %%V in (3.12 3.13 3.11) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
  )
)
if not defined PY (
  echo.
  echo *** No se encontro Python 3.12. Instalalo desde https://www.python.org/downloads/
  echo     y vuelve a ejecutar este archivo.
  goto error
)
echo     Creando entorno virtual con: %PY%
%PY% -m venv venv || goto error

:activar
call venv\Scripts\activate.bat

echo [2/6] Instalando librerias...
python -m pip install -q -r requirements.txt || goto error

echo [3/6] Revisando la configuracion local (.env)...
if not exist .env (
  copy .env.example .env >nul
  echo     Se creo el archivo .env a partir de .env.example. Revisalo si tu MySQL es distinto.
)

echo [4/6] Creando/actualizando las tablas en MySQL...
python manage.py migrate --noinput
if errorlevel 1 (
  echo.
  echo *** No se pudo conectar a MySQL. Revisa que:
  echo     - el servicio MySQL80 este iniciado,
  echo     - hayas ejecutado UNA vez docs\crear_base_datos.sql,
  echo     - los datos DB_ del archivo .env sean correctos.
  goto error
)

echo [5/6] Cargando datos de demostracion (si no existen)...
python manage.py cargar_demo || goto error

echo [6/6] Iniciando servidor en http://127.0.0.1:8000/
echo     Usuarios demo: administrador@condohub.cl, residente@condohub.cl, etc.
echo     Clave de todos: condohub2026     (para detener el servidor: Ctrl+C)
start "" http://127.0.0.1:8000/
python manage.py runserver
goto fin

:error
echo.
echo *** Ocurrio un error. Revisa el mensaje de arriba y la seccion
echo     "Problemas comunes" de DOCUMENTACION.md.
:fin
pause
