# Proposal

Issue: #75 (`Closes #75`). MoSCoW: Should. Cambio transversal: lo implementa Walther en todas las apps y avisa al unir.
Fuera de alcance: formato de montos (#76), formato y validación de RUT (#77), ayudas y secciones por formulario (#78), y todo JavaScript.

## Why

`templates/_formulario.html` dibuja cada campo bajo el otro sin `aria-describedby` ni `aria-invalid`, los errores no usan
`invalid-feedback`, los select muestran `---------` y el placeholder de Bootstrap no alcanza contraste AA (RNF de accesibilidad).
Los Issues #76, #77 y #78 necesitan un componente de campo común, por eso es el contrato C6 y debe unirse primero.

## What Changes

- Filtros `control` y `es_casilla` (`{% load formularios %}`): clase de Bootstrap según el widget y, con error, `is-invalid`,
  `aria-invalid="true"` y `aria-describedby` con ayuda y error.
- Plantilla `templates/_campo.html` con `prefijo` opcional (`input-group`), asterisco con `aria-hidden="true"` y errores con `invalid-feedback`.
- `_formulario.html` incluye `_campo.html` en su bucle: los 15 formularios actuales mejoran sin tocar sus plantillas.
- «Seleccione…» en vez de `---------` en los select, aplicado en `BootstrapMixin` (helper `rotular_vacios`).
- `templates/_opciones.html` (fieldset + legend) para `RadioSelect`.
- CSS: placeholder con contraste AA (`#6c757d`, `opacity: 1`) y `.subtitulo-seccion`.
- **Contrato C6:** `{% include "_campo.html" with campo=… prefijo=… %}`, filtros `control` y `es_casilla`. Se agrega al plan del PMV.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: nuevo requisito «Formularios accesibles», transversal a todas las páginas con formulario.

## Impact

- Código: `templates/_campo.html`, `_opciones.html` (nuevos), `templates/_formulario.html`, `apps/core/templatetags/formularios.py` (nuevo),
  `apps/core/formularios.py`, `static/css/condohub.css`, `apps/gastos/templates/gastos/reporte.html` (usa los campos a mano).
- Sin migraciones ni dependencias nuevas. Todas las apps ven el cambio visual; sin JavaScript el envío no cambia.
