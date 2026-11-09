# Design

## Context

Ver proposal.md (Why). Estado actual, leído en el código:

- Campos de dinero que escribe el usuario (grep de `monto`, `tarifa`, `IntegerField` en `apps/*/forms.py`):
  - `EgresoForm.monto` (`apps/gastos/forms.py`, `ModelForm`): `NumberInput` en `Meta.widgets` y `help_texts` «En pesos, sin puntos ni signo $».
    El modelo tiene `MinValueValidator(1)` y `MaxValueValidator(MONTO_MAXIMO)` (999.999.999).
  - `PagoForm.monto` (`apps/pagos/forms.py`, `forms.Form`, no `ModelForm`): `forms.IntegerField(label="Monto pagado ($)", min_value=1)`,
    `initial` = saldo y `clean_monto` contra el saldo.
  - `EspacioComunForm.tarifa` (`apps/reservas/forms.py`, `ModelForm`): `PositiveIntegerField(default=0)`, 0 = gratis.
  - Ningún otro: `alicuota` (condominios) y `porcentaje_fondo_reserva` (gastos) no son pesos. Los montos de cobros y fondo los calcula el sistema.
- Las tres plantillas usan `{% include "_formulario.html" with form=form %}`, que llama a `_campo.html` sin `prefijo`.
- `|pesos` (`apps/core/templatetags/condohub.py`): `None`/`""` → `$0`, no numérico → tal cual, redondea floats, negativos `-$5.000`.
  Lo usan 10 plantillas. En PDF solo existe `core/pdf/prueba.html` (texto fijo «$1.234.567»); #6 y #56 usarán `|pesos`.
- `base.html` no carga JS propio; termina con Bootstrap por CDN y `{% block scripts %}`.
- La prueba actual `test_montos_enteros_positivos` exige error para «0», «-500», «1500.5», «abc» y «1000000000»: debe seguir pasando.

## Goals / Non-Goals

**Goals:** una sola gramática y un solo formato de pesos, reutilizable por cualquier formulario futuro con una línea.

**Non-Goals:** decimales o monedas, formatear los montos en mensajes de error de `apps/pagos` (ya salen con puntos), cambiar `help_text` de modelos (crearía migración).

## Decisions

**Dónde vive cada pieza.** `apps/core/formato.py`: funciones puras, sin Django (`normalizar_monto`, `formatear_monto`), usables desde
filtros, formularios, PDF y pruebas; #77 agregará `formatear_rut` ahí mismo. `apps/core/campos.py`: `MontoInput` y `MontoField`, que
dependen de `django.forms`; #77 agregará `RutField`. No van en `apps/core/formularios.py` para no volver a tocar el archivo de C6
(mixins) y para que #76 y #77 trabajen en archivos que solo ellos editan. Alternativa descartada: todo en `formularios.py` (menos
archivos, pero mezcla estilo con lectura de datos y choca con #77/#78).

**Gramática estricta de `normalizar_monto(texto) -> str | None`.** Quita espacios en los extremos y un `$` inicial (con o sin espacio
después). El resto debe ser `^\d+$` o `^[1-9]\d{0,2}(\.\d{3})+$` (el primer grupo no empieza con 0); devuelve los dígitos sin puntos, o `None` si no calza. Así:
«$ 1.250.000», «1250000», « 85.000 » → válidos; «1,5», «1.5», «1500.5», «1.25.000», «0.500», «01.000», «-5», «abc», «1 250 000» → `None`. Sin puntos se mantiene `^\d+$`: «0» pasa a los validadores, que lo rechazan en el egreso y lo aceptan en la tarifa (0 = gratis).
En dinero, adivinar es peor que preguntar: «1.5» puede ser 1,5 o 1.500, y «1,5» no existe en pesos. Alternativa descartada: quitar todos
los puntos como en el reporte (convertiría «1500.5» en 15005 y rompe la prueba actual).

**`MontoField(forms.IntegerField)`.** `to_python`: vacío → `None` (el `required` lo maneja Django); si `normalizar_monto` da `None`,
`ValidationError(MENSAJE_MONTO_INVALIDO, code="invalid")` con «Escriba el monto en pesos, sin decimales. Ej.: 1.250.000.»
(constante, regla de negocio); si no, `super().to_python(digitos)`. Los negativos dan ese mismo mensaje. Hereda `min_value`/`max_value`.

**Validadores del modelo con `field_classes`.** En `EgresoForm` y `EspacioComunForm`: `field_classes = {"monto": MontoField}` /
`{"tarifa": MontoField}`. `PositiveIntegerField.formfield(form_class=MontoField)` sigue pasando `min_value=0`, `label` y `help_text`, y
`MinValueValidator(1)` y `MaxValueValidator(MONTO_MAXIMO)` del modelo se siguen ejecutando en `ModelForm._post_clean` (`full_clean`), con el
error en el campo `monto`. Hay que **quitar `monto` de `Meta.widgets`** del egreso: un `NumberInput` ahí anularía `MontoInput`. En `PagoForm`
basta `monto = MontoField(label="Monto pagado", min_value=1)` (el `$` ya va en el prefijo). Se prueba con «1.000.000.000» → error.

**`MontoInput(forms.TextInput)`.** Atributos por defecto `inputmode="numeric"`, `autocomplete="off"`, `data-monto`, placeholder «Ej.: 85.000»
(sobrescribibles). `format_value`: entero → `formatear_monto`; texto que `normalizar_monto` acepta → formateado; texto inválido → tal cual,
para que el usuario vea lo que escribió junto al error. Atributo de clase `prefijo = "$"`.

**Prefijo sin reescribir plantillas.** En `_campo.html`: `{% firstof prefijo campo.field.widget.prefijo as prefijo_campo %}` y usar
`prefijo_campo`. El `prefijo=` explícito de C6 sigue mandando; widgets sin el atributo no cambian. Es una extensión compatible del contrato C6
(misma firma). Alternativa descartada: pasar `prefijo` desde `_formulario.html` campo por campo (no conoce los campos).

**`|pesos` con `formatear_monto`.** Conserva sus ramas (`None`/`""` → `$0`, no numérico → tal cual, `round(float(...))`, signo antes del `$`) y
solo delega `f"{n:,}".replace(...)` a `formatear_monto(abs(n))`. Prueba parametrizada con la salida actual antes de tocarlo.

**JS `static/js/formato.js`.** Archivo único, sin npm ni build, cargado en `base.html` con `<script src="{% static 'js/formato.js' %}" defer>`
antes de `{% block scripts %}`. Contiene `reformatear(entrada, formatear, esSignificativo)` (cursor tras el mismo dígito) y un registro
`FORMATOS = { monto: { formatear: formatearMonto, significativo: digito } }`. Un solo listener `input` delegado en `document` busca
`[data-<clave>]` por cada clave del registro, así sirve en formularios cargados después. #77 solo agrega `rut: {...}`.
**El JS nunca cambia un monto sin avisar.** Reglas de `formatearMonto` y del listener:
- Mientras se escribe, solo reagrupa los puntos que el propio JS pone: si el usuario tipea un punto o una coma (`InputEvent.data`), o pega un texto que no es un monto válido según la gramática del servidor (réplica de `normalizar_monto`), el JS marca `dataset.montoManual` en ese campo y deja de formatearlo hasta que quede vacío. Así «1500.5» no se convierte en «15.005» ni se guarda 15005: el servidor lo rechaza y muestra el error.
- Pegar «$ 1.250.000» (monto válido) se formatea normalmente.
- Al salir del campo (`blur`) da formato solo si el texto es un monto válido; si no, lo deja tal cual.
- Ante coma, letra o `-` nunca toca el valor. Sin JS, el servidor acepta las mismas entradas.
- La lógica va en funciones puras (`esMontoValido`, `formatearMonto`, `reformatear`) y, como el proyecto no tiene ejecutor de JS, se prueba en el navegador con `javascript_tool` y se anotan los casos en el PR.

## Risks / Trade-offs

- [Pegar «1 250 000» con espacios internos se rechaza] → el mensaje da el ejemplo correcto; preferible a adivinar.
- [`base.html` es archivo compartido] → una línea, avisada al unir; #26 agrega otra en otra parte.
- [Ramas de Winderson y Maximiliano tocan `pagos/forms.py` y `reservas/forms.py`] → cambio de una o dos líneas, aviso en el grupo y PR pequeño.
- [Pruebas existentes que envían `monto="85990"`] → siguen válidas (sin puntos es aceptado).

## Migration Plan

Sin migraciones ni datos. Revertir es deshacer el PR: los datos guardados no cambian.
