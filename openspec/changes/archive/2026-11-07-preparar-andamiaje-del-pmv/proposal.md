# Proposal

Closes #62 · MoSCoW: **Must** (hito PMV 27-nov) · Contrato C0 de `docs/equipo/PLAN_PMV_27NOV.md`.

## Why

Los tres integrantes trabajarán en paralelo hasta el 24 de noviembre. Si cada uno agrega su app a `settings.py`,
`urls.py`, `base.html` y `cargar_demo.py`, o elige su propia librería de PDF, los PR chocan. Este cambio deja listas
las piezas comunes en un PR corto que se une el lunes 9.

## What Changes

- **Período con vencimiento y reglamento:** `PeriodoGasto` gana `fecha_vencimiento` (por defecto, el día 10 del
  mes siguiente) y `referencia_reglamento` (obligatoria si el criterio es partes iguales, como pide la Ley 21.442).
  El formulario y el detalle del período los muestran. Es el único cambio de comportamiento.
- **PDF (C0):** `apps/core/pdf.py` con `renderizar_pdf(plantilla, contexto, nombre)`, que devuelve un `HttpResponse`
  con el PDF, y una plantilla base para los documentos. Librería xhtml2pdf con sus dependencias fijadas.
- **Demo por app:** cada app tiene `demo.py` con `cargar(datos)`, y `cargar_demo` los llama en orden. Los datos que
  se cargan no cambian.
- **Apps nuevas:** `auditoria`, `privacidad`, `cartera` y `rendicion`, registradas en `settings.py` y `urls.py`,
  con una página provisional y su enlace en el menú "Administración" o en el pie ("Aviso de privacidad").

## Capabilities

### New Capabilities

Ninguna. Las apps nuevas solo tienen páginas provisionales; sus specs llegan con sus Issues (#27, #51, #54, #55).

### Modified Capabilities

- `gastos-comunes`: «Período mensual de gastos» suma la fecha de vencimiento y la referencia del reglamento.

## Impact

- Código: `apps/gastos` (modelo, formulario, plantillas y la migración `0006`), `apps/core` (`pdf.py`, plantilla
  base del PDF, `cargar_demo`), `config/`, `templates/base.html`, un `demo.py` por app y cuatro apps nuevas.
- Dependencias: `xhtml2pdf==0.2.28` y 12 dependencias con ruedas para Windows y Linux.
- Equipo: después de unir, nadie más edita `settings.py`, `urls.py` ni `cargar_demo.py`. Toca carpetas de
  Maximiliano y Winderson (solo `demo.py` y las apps nuevas), así que se pide su revisión.

## Fuera del alcance

- Modelos, vistas reales y specs de auditoría, privacidad, cartera y rendición (#27, #51, #54, #55).
- Aviso de cobro y comprobante en PDF (#6, #56): aquí solo está la función y un PDF de prueba.
- Recargos o intereses por pago atrasado, y el día de vencimiento configurable por condominio.
- Registrar en auditoría la creación y edición del período: espera el contrato C1 (#27).
