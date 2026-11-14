# Demo aislada del cliente (Issue #93)

Todos los condominios, personas, cuentas y montos de esta demo son ficticios.
Usar desde la raíz del repositorio, con su entorno virtual y dependencias ya instaladas.

En PowerShell, preparar y arrancar con estos dos comandos:

```powershell
venv\Scripts\python.exe manage.py preparar_demo_cliente --settings=config.settings_demo
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8016 --settings=config.settings_demo
```

Antes de migrar o cargar, la preparación debe mostrar el motor
`django.db.backends.sqlite3` y la ruta absoluta
`<raíz del repositorio>\.demo_cliente\demo.sqlite3`. Si no coincide, detenerse.
El comando rechaza otro motor, rutas relativas, rutas fuera de `.demo_cliente/`
y enlaces que salen de ese directorio, antes de crear carpetas, migrar o cargar.
`.env` y las bases habituales no se modifican. La carpeta `.demo_cliente/` completa
(base, registros y evidencias locales) está ignorada por Git.

Abrir [la demo local](http://127.0.0.1:8016/). Las cuentas ficticias por rol y su
clave de demostración siguen siendo las de la tabla de `README.md`; la preparación
también las muestra. Gerencia conserva acceso a los dos condominios.
Las cookies de sesión y CSRF tienen nombres propios para no desplazar la sesión
del servidor habitual en otro puerto de localhost. Cerrar este servidor con
`Ctrl+C` en su propia terminal al terminar.

La fecha de referencia es el 16-nov-2026: Vista Verde tiene septiembre y octubre
emitidos y noviembre abierto; Los Aromos tiene octubre emitido. El fondo usa C5:
aperturas ficticias del 31-ago, aportes creados por las emisiones y un egreso
ficticio de ascensor por $75.000 con acuerdo documentado. Los saldos son
$1.140.537 en Vista Verde y $533.925 en Los Aromos. Son saldos contables del fondo,
no efectivo recaudado.

Repetir la preparación migra lo pendiente y conserva todos los registros existentes;
no duplica ejemplos ni regenera la base. Si hay un error de carga, revisar su mensaje
y corregir la causa antes de repetir. No borrar la base ni usar `--reiniciar` como
recuperación. Una regeneración destructiva queda fuera de este comando.

Contrato para los otros cargadores: `cargar_demo` entrega
`datos['fecha_referencia_demo']` únicamente si existe `DEMO_FECHA_REFERENCIA` en la
configuración. Conserva las otras claves y el orden `APPS_DEMO`. Sin esa opción,
la carga normal mantiene fechas y huella. Los ejemplos de comunidad/operación
para el lunes se integran mediante sus propios Issues; esta preparación no los sustituye.

Las pruebas y controles de desarrollo siguen usando MySQL; esta SQLite sirve solo
para la demostración local, sin cambiar modelos, permisos ni cálculos.
