# Design

## Context

Ver proposal.md (Why). Estado actual, leído en el código:

- `apps/cuentas/validadores.py` tiene `normalizar_rut`, `calcular_dv` y `validar_rut` (regex `(\d{7,8})-([\dK])`). Lo importan `cuentas` (forms, models),
  `proveedores` (forms, models), `condominios/importacion.py` y las migraciones (`validar_rut`). `apps/core` no depende de `cuentas`.
- Formularios donde se escribe un RUT: `FormularioAltaUsuario.rut` (`forms.CharField`, `cuentas`), `FormularioPerfil` (`ModelForm`, campo `rut`, opcional) y
  `ProveedorForm` (`ModelForm`, `rut`). `ResidenteForm` busca por correo: no pide RUT. Fuera: `FormularioCrearUsuario`/`FormularioEditarUsuario` (admin de Django).
- Donde se muestra: `cuentas/usuarios.html` (`u.rut|default:"—"`) y `proveedores/lista.html` (`p.rut`). `unidades.html` muestra al residente solo por nombre.
  Ningún PDF muestra RUT hoy (`core/pdf/prueba.html` no lo usa). `Proveedor.__str__` devuelve «razón (rut)».
- Roles: usuarios, alta y proveedores nuevo/editar son de ADMINISTRADOR; la lista de proveedores y la de unidades también las ve COMITE.
- `formato.js` ya tiene `reformatear`, `FORMATOS` (monto) y la regla «el JS nunca cambia un valor sin avisar». `control` (C6) arma `aria-describedby` con `<id>_helptext` y `<id>_error`.

## Goals / Non-Goals

**Goals:** el RUT se escribe como cada quien quiera, se avisa su estado en vivo de forma accesible, se guarda normalizado y se ve con puntos en listados.

**Non-Goals:** cambiar la validación del servidor, aceptar RUT sin guion, ni tocar el admin de Django.

## Decisions

**Dónde vive `formatear_rut` y sentido de las importaciones.** Las funciones puras pasan a `apps/core/formato.py` (que ya declara «sin Django»):
`normalizar_rut`, `calcular_dv`, `RUT_FORMATO` (regex compilada) y `formatear_rut`. `apps/cuentas/validadores.py` las importa desde `core` y las reexporta con
`__all__`, y conserva `validar_rut` (usa `ValidationError` y `RUT_FORMATO`). Sentido único: `cuentas → core`, el mismo que ya tienen los demás módulos;
`core` nunca importa `cuentas`. No se duplica nada: se mueve el código. Los imports actuales (`from apps.cuentas.validadores import normalizar_rut`) y las
migraciones siguen válidos, así que Maximiliano y Winderson no tocan esas líneas. Alternativa descartada: que `core` importe de `cuentas` (invierte la dependencia y arriesga ciclos).

**`formatear_rut(valor)`.** Normaliza; si calza `RUT_FORMATO` agrupa el cuerpo de a tres dígitos con punto (por texto, sin `int()`, para no borrar ceros) y devuelve `cuerpo-DV`; si no, devuelve el valor tal cual.
`12345678-5` → `12.345.678-5`; `1234567-4` → `1.234.567-4`; `96511790-K` → `96.511.790-K`; `abc` y `123456785` quedan igual. No comprueba el dígito verificador: mostrar no es validar, y un dato antiguo mal escrito debe verse como está.

**Filtro `|rut`, no propiedades `rut_visible`.** Se elige el filtro. (1) Sirve para cualquier texto (cuerpo de correo, PDF, datos de la importación) sin elegir un modelo; `Residente` ni siquiera tiene RUT propio y necesitaría una propiedad que delegue en `usuario`. (2) Es el patrón de `|pesos` (#76). (3) Las propiedades tocarían `models.py` de tres apps de otros integrantes; el filtro cambia una línea de plantilla. (4) Una sola función pura, probada una vez. Costo: hay que acordarse de aplicar `|rut`; se mitiga con las pruebas de listados y la guía. `None` y `""` dan `""`, para encadenar `|rut|default:"—"`.
`Proveedor.__str__` también usa `formatear_rut`, porque aparece en listas desplegables y mensajes; es solo texto, sin migración.

**Dónde se muestra.** `usuarios.html` y `proveedores/lista.html` con `|rut`. En Unidades, bajo el nombre del residente, solo con `es_admin`: el comité hoy ve esa página sin datos personales y no se amplía esa exposición. Cubre el criterio «residentes» del Issue.

**`RutInput` y `RutField` (`apps/core/campos.py`).** `RutInput(forms.TextInput)`: `data-rut`, `autocomplete="off"`, `spellcheck="false"`, `autocapitalize="characters"`, placeholder `12.345.678-5` (ficticio, DV correcto; sobrescribible), atributo de clase `aviso_vivo = True` y `format_value` con `formatear_rut` (un valor inválido se devuelve tal cual, para verlo junto al error).
`RutField(forms.CharField)`: `max_length=12`, `validators=[validar_rut]` y `to_python` que devuelve `normalizar_rut(valor)`, así `cleaned_data["rut"]` siempre sale normalizado (`12345678-5`); vacío → `""` (opcional en el perfil). `validar_rut` no cambia, y los mensajes («Formato de RUT inválido…», «El dígito verificador…») tampoco.
Aplicación, una línea por formulario: alta → `rut = RutField(label="RUT", help_text=…)`; perfil y proveedor → `field_classes = {"rut": RutField}` en `Meta` (se conserva el validador del modelo). No se toca `models.py` (cambiar su `help_text` crearía una migración).

**Aviso `aria-live` sin chocar con C6.** `_campo.html` agrega, solo si `campo.field.widget.aviso_vivo`, un `<div class="form-text" id="<id>_aviso" aria-live="polite" data-rut-aviso></div>` vacío, tras el control y antes de la ayuda. `control` agrega `<id>_aviso` a `aria-describedby` cuando el widget lo pide, en el orden ayuda, aviso, error. Las firmas de `_campo.html` y de los filtros no cambian y los campos sin `aviso_vivo` salen idénticos (prueba). Sin JS el div queda vacío y no estorba. El JS no crea el elemento: solo escribe en él, y si no existe, no avisa. El error del servidor sigue en `<id>_error`.

**JS (`static/js/formato.js`).** Se agrega `rut` al registro `FORMATOS` con la forma de `monto` (`enVivo`, `alSalir`, `esValido`, `significativo`, `pideDetenerse`), reutilizando `reformatear`. Funciones puras: `normalizarRut`, `formatearRut`, `calcularDv`, `rutValido`, con la misma gramática que `RUT_FORMATO` (Python es la fuente; los ejemplos de las pruebas de `formatear_rut` se repiten como casos en el navegador).
Regla «no cambiar sin avisar», distinta de la receta del reporte, que descarta en silencio las letras y todo lo que pasa de 9 caracteres:
- En vivo solo se reformatea si el texto tiene únicamente dígitos, K/k, puntos, guion y espacios, a lo más 9 dígitos/K y la K solo al final. Los puntos y el guion los pone el propio JS; la `k` pasa a `K`.
- Si la persona escribe otro carácter (letra que no sea K, coma, signo), una K antes del final o más de 9 dígitos, o pega algo que no cumple, se marca `dataset.rutManual` y el JS deja de tocar el campo hasta que quede vacío, como `montoManual`. El servidor muestra el error.
- El último carácter significativo se trata como dígito verificador: «123456785» → «12.345.678-5». Con cuerpo de 7 dígitos, «12345674» → «1.234.567-4», que es válido (el servidor acepta 7 u 8 dígitos).
- Aviso: con 8 o más caracteres significativos y formato reconocible, si el DV cuadra se escribe «RUT válido.» (`text-success`) y se borra cuando deja de cumplirse. Mientras se teclea nunca se escribe un error.
- Al salir (`focusout`): si el campo no está vacío y no es un RUT con DV correcto, el aviso muestra el texto del servidor («El dígito verificador del RUT no es correcto.» o «Formato de RUT inválido. Ejemplo: 12.345.678-5») con `text-danger`, y el campo recibe `aria-invalid="true"` e `is-invalid`, que se quitan al volver a escribir.
- Un formulario que vuelve con error trae el valor ya formateado por `format_value`; al entrar al campo, si es inválido se marca manual (como en monto).
- Como no hay ejecutor de JS en el proyecto, se prueba en el navegador con `javascript_tool` y los casos se anotan en el PR.

**Sin JavaScript.** El servidor acepta las mismas entradas que hoy (con o sin puntos, con guion, `k` minúscula) y guarda `normalizar_rut`. `Usuario.save` y `Proveedor.save` ya normalizan, y `RutField` lo hace además antes de las comprobaciones de unicidad (`validar_rut_disponible`, `clean_rut` del proveedor). Lo guardado no cambia.

**RUT con K y cuerpo de 7 dígitos.** La K es válida solo como DV, en mayúscula al guardar (`calcular_dv` da `K` cuando el resto es 10, y el JS replica la regla). El cuerpo de 7 dígitos es válido y se muestra `1.234.567-4`. Un cuerpo de 6 o de 9 dígitos sigue siendo inválido.

## Risks / Trade-offs

- [Pegar «12345678 5» con espacio interno] → el servidor ya lo acepta (quita espacios) y el JS también.
- [Cambiar `Proveedor.__str__` altera textos que usan pruebas de otras apps] → se revisan con grep antes y se actualizan en el mismo PR.
- [`_campo.html` y `formularios.py` los comparte #78] → cambio acotado y avisado al unir.
- [Mover funciones de `cuentas` a `core` con ramas abiertas] → el reexport evita conflictos de imports; solo cambia `validadores.py`.
- [Mostrar RUT a administradores en Unidades] → decisión de privacidad a aprobar; el comité no lo ve.

## Migration Plan

Sin migraciones ni datos. Revertir es deshacer el PR.
