# Proposal

Closes #57 · MoSCoW: **Should** · Hito PMV 27-nov · NTI-04 (Informe 1).

## Why

Hoy el administrador conoce la morosidad recién al abrir el reporte, y el residente se entera de que debe solo si entra a «Mi cuenta». Un aviso antes y después del vencimiento, y los indicadores a la vista en el panel de inicio, ayudan a cobrar a tiempo.

## What Changes

- **Comando `enviar_recordatorios`:** avisa por la campana y por correo (patrón Observer) a los residentes con saldo en un período emitido:
  - **antes del vencimiento:** en los 3 días previos;
  - **después del vencimiento:** desde el día siguiente, hasta 7 días después (por si el comando no corrió algún día).
  Cada persona recibe cada aviso una sola vez por cobro, aunque el comando corra varias veces. Acepta `--fecha` para simular el día.
- **No avisa** a quien ya pagó, a quien no quiere correos (solo recibe la campana) ni a residentes fuera de su período (#46).
- **Indicadores de cobranza en el panel de inicio** del administrador y del comité, del último período emitido: % de recaudación, deuda total y unidades morosas, con enlace al reporte.

**Fuera del alcance:**
- Programar la ejecución diaria en el servidor (cron): es parte del despliegue (#29, Walther). Se deja documentado el comando.
- Avisos por WhatsApp o SMS.
- Configurar los días de anticipación por condominio.
- Datos demo propios: generar avisos en `cargar_demo` cambiaría la cantidad de notificaciones según el día. En la demo se ven corriendo el comando con `--fecha`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `comunicacion`: se agrega el requisito «Recordatorios de pago».
- `reportes`: se agrega el requisito «Indicadores de cobranza».

## Impact

- **Mis carpetas:**
  - `apps/notificaciones`: modelo `RecordatorioEnviado` y su migración, módulo de recordatorios, comando y pruebas.
  - Panel de inicio: `InicioView` (`apps/core/views.py`) y `core/inicio.html`, que el plan me asigna durante el PMV.
- **Solo lee:** `cobros_visibles` (C2, #46), `saldo_del_cobro` de `apps/pagos` y `generar_reporte` de `apps/gastos/reportes.py`.
- **Sin cambios** en `config/`, `templates/base.html` ni `requirements.txt`.
- **Dependencias:** `fecha_vencimiento` (#62, en `main`); el correo real llega con el despliegue (#29).
