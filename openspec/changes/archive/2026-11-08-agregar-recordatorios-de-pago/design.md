# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver las specs `comunicacion` y `reportes` de este cambio.

Estado actual que condiciona el diseño:

- `PeriodoGasto.fecha_vencimiento` (#62) ya existe: por defecto, el día 10 del mes siguiente.
- `cobros_visibles(cobros, usuario)` (C2, #46) decide qué cobros ve un residente activo según su período de residencia.
- `saldo_del_cobro` (`apps/pagos/consultas.py`) y `generar_reporte` (`apps/gastos/reportes.py`) ya calculan saldos, recaudación y morosidad. Se usan sin cambiarlos.
- El Observer (`apps/notificaciones/observador.py`) ya tiene la campana y el correo; `NotificadorCorreo` respeta `recibir_correos` y envía con `on_commit`.
- El panel de inicio (`InicioView`, `core/inicio.html`) ya muestra un resumen al administrador, al comité y al conserje.

## Goals / Non-Goals

**Goals:**

- Avisar a tiempo sin repetir avisos, aunque el comando corra varias veces o se salte un día.
- Que los indicadores del inicio den los mismos números que el reporte.
- Probar todo con fechas simuladas.

**Non-Goals:**

- Programar el cron en el servidor, otros canales (WhatsApp, SMS) y días configurables por condominio.

## Decisions

### D1. Ventanas de aviso

Con `hoy` y el vencimiento `v` de cada período emitido:

- **ANTES:** si faltan entre 1 y 3 días (`v - 3 ≤ hoy ≤ v - 1`).
- **DESPUÉS:** si pasaron entre 1 y 7 días (`v + 1 ≤ hoy ≤ v + 7`).

El día del vencimiento no se envía nada: ya llegó el aviso previo. Usar ventanas, y no días exactos, cubre un día en que el comando no corrió; D2 evita que se repita.

### D2. `RecordatorioEnviado`: un aviso por cobro, persona y tipo

Modelo nuevo en `apps/notificaciones` (migración `0002`):

- `cobro` (FK a `DetalleGastoComun`, CASCADE), `usuario` (FK, CASCADE), `tipo` (ANTES o DESPUES) y `enviado` (fecha y hora).
- Restricción única `(cobro, usuario, tipo)`.

Antes de avisar se crea el registro, en la misma transacción que la notificación. Si ya existe (otra ejecución lo creó antes), se omite ese aviso.

### D3. A quién se avisa

1. Períodos emitidos de condominios activos, con el vencimiento dentro de alguna ventana.
2. Sus cobros no pagados con `saldo_del_cobro(cobro) > 0`.
3. Los residentes activos de esas unidades. Para cada persona, `cobros_visibles(cobros, usuario)` deja solo los cobros de su período de residencia (C2): quien llegó después o fue dado de baja no recibe aviso.
4. Se descartan los que ya tienen su `RecordatorioEnviado`.

### D4. Observer: `Recordatorio` como sujeto

`Recordatorio` es una clase simple (no un modelo) que hereda de `Sujeto`, en `apps/notificaciones/recordatorios.py`. Se suscribe a la campana y al correo en `apps.py`, como los demás sujetos. Cada aviso es un `Evento` para una persona, con el monto que debe, el período, la fecha de vencimiento y el enlace a su cobro (`pagos:cobro_detalle`). El correo respeta `recibir_correos` porque lo hace `NotificadorCorreo`.

### D5. Comando

`python manage.py enviar_recordatorios [--fecha AAAA-MM-DD]`. Sin `--fecha` usa el día de hoy. Al terminar imprime cuántos avisos envió de cada tipo. La lógica vive en una función `enviar_recordatorios(hoy)` que las pruebas llaman con fechas simuladas. Programarlo cada día en el servidor queda para el despliegue (#29).

### D6. Indicadores en el panel de inicio

En `InicioView`, solo para administrador y comité (el conserje no ve dinero):

- Último período emitido del condominio (el mismo que el reporte muestra por defecto).
- `generar_reporte(periodo)`: `porcentaje_recaudacion`, `deuda_total` y `len(unidades_morosas)`.
- Tarjetas con enlace a `gastos:reporte`. Sin períodos emitidos, un texto lo indica.

### D7. Auditoría

Los recordatorios no cambian dinero, roles ni datos personales: no registran evento de auditoría (#27).

## Risks / Trade-offs

- **Correo real:** hasta el despliegue (#29), en desarrollo los correos salen en la consola.
- **Huella de la demo:** `cargar_demo` no envía recordatorios, para no cambiar la cantidad de notificaciones según el día (`CargarDemoTest`).
- **Consultas:** una consulta de `cobros_visibles` por residente con saldo. Con 200 unidades es aceptable para un comando diario.
- **Inicio:** los indicadores arman el reporte completo del período en cada visita. Es el precio de que los números coincidan siempre con el reporte; con 200 unidades es aceptable.
