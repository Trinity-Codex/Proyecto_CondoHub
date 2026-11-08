# Design

## Context

Ver `proposal.md` (Why). Estado actual: `PeriodoGasto` (`apps/gastos/models.py`) no tiene vencimiento ni
referencia del reglamento; `PeriodoForm` pide mes, año, % del fondo y criterio. `cargar_demo.py` (261 líneas) crea
todo en métodos privados que mezclan apps. `requirements.txt` no tiene librería de PDF. Hay 243 pruebas.

## Goals / Non-Goals

**Goals:** entregar el contrato C0 con la firma exacta del plan y que nadie más necesite editar `settings.py`,
`urls.py`, `base.html` ni `cargar_demo.py` durante el PMV.

**Non-Goals:** diseño visual de los documentos PDF; modelos en las apps nuevas (no tienen migraciones).

## Decisions

### 1. Librería de PDF: xhtml2pdf 0.2.28 (recomendada)

| | xhtml2pdf 0.2.28 | fpdf2 2.9.0 |
|---|---|---|
| Entrada | Plantilla HTML de Django con CSS básico (tablas, fuentes, márgenes) | Código Python celda por celda; su HTML es muy limitado |
| Dependencias | 12: reportlab 5.1.0, pillow, lxml, pypdf, html5lib, svglib… | 2: fonttools, pillow |
| Ruedas (cp312) | `py3-none-any`, `win_amd64` y `manylinux_2_28`: no compila nada | Igual |
| Licencia | Apache-2.0 (reportlab BSD) | LGPL-3.0 |

Se recomienda **xhtml2pdf** porque la firma recibe una *plantilla*: el aviso de cobro (#6) y el comprobante (#56) se
escriben como cualquier plantilla de Django y se prueban leyendo el texto con `pypdf`, que ya viene como
dependencia. Costo: no admite flexbox ni grid (se maqueta con tablas) y suma más paquetes. Con fpdf2 el parámetro
`plantilla` no tendría sentido. WeasyPrint se descarta porque necesita GTK en Windows. Las versiones se resolvieron
con `pip install --dry-run` para Windows y para `manylinux_2_28` (la CI) el 7 de noviembre.

### 2. Contrato `renderizar_pdf`

```python
# apps/core/pdf.py
def renderizar_pdf(plantilla: str, contexto: dict, nombre: str) -> HttpResponse
```

- Renderiza `plantilla` con `render_to_string(plantilla, contexto)` (sin `request`: el contexto trae todo lo que
  la plantilla usa) y la convierte a PDF.
- Devuelve un `HttpResponse` con `Content-Type: application/pdf` y
  `Content-Disposition: inline; filename="<nombre>.pdf"`: el navegador lo abre y se puede descargar. `nombre` va
  sin extensión (se agrega `.pdf` si falta) y se limpia con `get_valid_filename`.
- Si la conversión falla, lanza `ErrorPDF` (no entrega un PDF roto).
- Las imágenes y el CSS solo se leen de `static/` con los *finders* de Django; las URL externas se ignoran, para
  que una plantilla no haga solicitudes a otros servidores.
- Ayudante para pruebas y correos: `generar_pdf(plantilla, contexto) -> bytes`, que `renderizar_pdf` usa.
- Plantilla base `core/pdf/base.html` (márgenes, logo, pie con fecha de generación) con los bloques `titulo` y
  `contenido`; los documentos la extienden.

### 3. Vencimiento y referencia del reglamento

- `fecha_vencimiento = DateField(blank=True)`. Si llega vacía, `save()` usa
  `vencimiento_por_defecto(anio, mes)`: día `DIA_VENCIMIENTO = 10` del mes siguiente. El formulario la propone
  como valor inicial y rechaza una fecha anterior al primer día del mes siguiente.
- `referencia_reglamento = CharField(max_length=200, blank=True)`, validada en `PeriodoGasto.clean()` para que
  también aplique en el admin de Django.
- Migración `gastos/0006`: agrega el campo nulo, lo completa con `RunPython` y lo deja obligatorio. Es la única
  del PR.

### 4. Demo por app

Cada `apps/<app>/demo.py` expone `cargar(datos: dict) -> None` y agrega a `datos` lo que otras apps usan:
`usuarios`, `vista_verde`, `los_aromos`, `unidades` ("A-101"…), `proveedores` y `periodos`. `cargar_demo`
conserva `--reiniciar` y la transacción, y llama en este orden: cuentas, condominios, reservas, comunicados,
incidentes, proveedores, gastos, pagos, notificaciones, auditoria, privacidad, cartera, rendicion (las cinco
últimas, vacías). Que los datos no cambian se prueba con una "huella" de conteos y sumas, no de `pk`, porque el
orden de creación sí cambia.

### 5. Apps nuevas

Cada una con `apps.py`, `urls.py` (`app_name`), `views.py`, `templates/<app>/provisional.html`, `tests.py` y
`demo.py`, sin modelos. Vistas `TemplateView` con `RolRequeridoMixin` y `CondominioQuerysetMixin` (este último
queda listo para cuando la app tenga modelo).

| App | URL y nombre | Roles provisionales | Enlace |
|---|---|---|---|
| auditoria | `/auditoria/` · `auditoria:inicio` | Administrador | Menú Administración |
| cartera | `/cartera/` · `cartera:inicio` | Administrador, comité | Menú Administración |
| rendicion | `/rendicion/` · `rendicion:inicio` | Administrador, comité | Menú Administración |
| privacidad | `/privacidad/` · `privacidad:aviso` | Público, sin sesión | Pie de página |

El aviso de privacidad es la única vista sin `RolRequeridoMixin`: se debe poder leer antes de iniciar sesión.

## Risks / Trade-offs

- [xhtml2pdf no entiende CSS moderno] → la plantilla base usa tablas y se documenta en `docs/GUIA_NUEVA_FEATURE.md`.
- [Separar la demo cambia los datos sin que nadie lo note] → la prueba de huella se escribe y pasa **antes** de
  mover el código.
- [Editar `demo.py` de otros integrantes] → se pide revisión a Maximiliano y Winderson antes de unir.
- [Un período nuevo de partes iguales en la demo] → la demo actual usa alícuota: no requiere referencia.
