Issue: #79 (`Closes #79`). MoSCoW: Could (UI-5 del reporte de mejoras de interfaz). Depende de #57 (unido).
Fuera de alcance: filtros y chips en los listados (#80), las insignias `.insignia-*`, el panel del residente, la
«rendición del mes» del comité (la app `rendicion` aún es una página provisional) y cualquier migración.

## Why

El panel del administrador muestra cifras sueltas (unidades, residentes, incidentes abiertos, reservas de hoy) y la
cobranza de #57, pero ninguna lleva a la lista donde se actúa, y el estado de las unidades (al día, con deuda,
morosa) solo se ve dentro del reporte. Quien administra necesita saber de un vistazo qué requiere acción y llegar
a ello con un clic. Entrega PMV: 27 de noviembre de 2026.

## What Changes

- Una grilla de tarjetas `.kpi` por estado, cada una un enlace entero con nombre, cantidad y una frase:
  unidades al día, con deuda y morosas; incidentes recibidos y en proceso; reservas próximas.
- Cantidades y textos armados en `InicioView`; la plantilla solo los recorre. Las unidades salen del reporte que
  #57 ya genera (`generar_reporte`), sin recalcular la morosidad.
- Paleta por estado en variables CSS (`--estado-*`) con contraste AA comprobado, para que #80 la reutilice.
- El resumen actual conserva «Unidades» y «Residentes»; «Incidentes abiertos» y «Reservas hoy» pasan a tarjetas.
  La tarjeta de cobranza conserva recaudación y deuda total; las unidades morosas pasan a su tarjeta.
- Los enlaces usan `?estado=` donde el listado ya lo acepta (incidentes). Para unidades se define `?situacion=`
  como contrato para #80; mientras tanto el enlace abre el reporte sin filtro.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: se agregan «Panel con tarjetas por estado» y «Colores por estado accesibles» (ADDED).
- `reportes`: se modifica «Indicadores de cobranza»; las unidades morosas pasan a la tarjeta por estado.

## Impact

- **Código:** `InicioView` y `core/inicio.html` (Maximiliano), `static/css/condohub.css` (Walther), pruebas en
  `apps/core/tests.py`. Sin migraciones ni dependencias.
- **Otros integrantes:** se avisa a Maximiliano al unir. Las variables `--estado-*` son el contrato de colores de #80.
- **Datos demo:** los datos de `apps/gastos/demo.py`, `incidentes/demo.py` y `reservas/demo.py` ya alcanzan; se verifica.
