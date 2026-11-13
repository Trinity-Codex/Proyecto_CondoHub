# Proposal

Issue: #76 (`Closes #76`). MoSCoW: Should. Cambio transversal: lo implementa Walther en `apps/core`, `apps/gastos`,
`apps/pagos` (Winderson) y `apps/reservas` (Maximiliano), con aviso al unir. Depende de #75 (contrato C6, ya en `main`).
Fuera de alcance: RUT (#77, que reutilizará el JS), ayudas y secciones por formulario (#78), decimales, UF u otras monedas,
y los montos que el sistema calcula (cobros, fondo de reserva): solo cambian los campos que el usuario escribe.

## Why

Un usuario chileno escribe «1.250.000» y Django lo rechaza; la ayuda del egreso pide «sin puntos ni signo $». Además «1250000»
es difícil de leer y verificar al registrar un egreso o un pago. Es la entrada de dinero de la app, por eso es de nivel A.

## What Changes

- Funciones puras `normalizar_monto` y `formatear_monto` (`apps/core/formato.py`, nuevo).
- `MontoInput` y `MontoField` (`apps/core/campos.py`, nuevo): texto con `inputmode="numeric"`, acepta «$ 1.250.000», «1.250.000»
  y «1250000»; rechaza decimales, comas, negativos, letras y puntos mal agrupados con un mensaje claro en español. Muestra el
  monto con puntos al abrir el formulario y al volver con error. Respeta `MinValueValidator` y `MONTO_MAXIMO` del modelo.
- Prefijo `$` automático en `_campo.html` para los campos de monto, sin editar las plantillas que usan `_formulario.html`
  (extensión compatible de C6: el `prefijo=` explícito sigue mandando).
- JS progresivo `static/js/formato.js` cargado en `base.html`: agrega los puntos mientras se escribe en `[data-monto]`,
  dejando el cursor en su lugar. Preparado para que #77 registre `[data-rut]`. Sin JavaScript todo funciona igual.
- `|pesos` pasa a usar `formatear_monto` con la misma salida de hoy (`$1.234.567`, `-$5.000`, `$0`).
- Campos que cambian: `monto` de `EgresoForm` (gastos), `monto` de `PagoForm` (pagos) y `tarifa` de `EspacioComunForm` (reservas).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: nuevo requisito «Montos en pesos legibles», transversal a los formularios con dinero.

## Impact

- Código: `apps/core/formato.py` y `apps/core/campos.py` (nuevos), `apps/core/templatetags/condohub.py`, `templates/_campo.html`,
  `templates/base.html` (una línea), `static/js/formato.js` (nuevo), `apps/gastos/forms.py`, `apps/pagos/forms.py`,
  `apps/reservas/forms.py`, y pruebas en `apps/core/tests.py`, `apps/gastos/tests.py`, `apps/pagos` y `apps/reservas`.
- Sin migraciones (los modelos siguen con `PositiveIntegerField` y sin cambiar `help_text`), sin dependencias ni npm.
- Lo guardado no cambia: siguen siendo enteros en pesos. Contratos C0 a C6 sin cambios de firma.
