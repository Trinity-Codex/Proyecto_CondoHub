# Design

## Context

`_formulario.html` recorre los campos de 15 formularios (20 `include`). `apps/core/formularios.py` ya ofrece `BootstrapMixin`, que
agrega `form-control`, `form-select` o `form-check-input` al `attrs["class"]` de cada widget al crear el formulario. Dos páginas
dibujan campos a mano: `gastos/reporte.html` (filtro con `{{ form.periodo }}`) y `condominios/importar.html` (una casilla que no es campo de Django).
Hay `empty_label` propios: «Sin proveedor» y «Todos los edificios». `ModelChoiceField(empty_label=None)` en `periodo` del reporte.
Referencia: reporte de mejoras §2 y §8 (adaptado; sin nombres ni reglas de Tattersall).

## Goals / Non-Goals

**Goals:**
- Un componente por campo reutilizable por #76, #77 y #78 y por grillas de 2 o 3 columnas.
- Que los formularios actuales mejoren sin editar sus plantillas.

**Non-Goals:** máscaras y formato de montos o RUT, textos de ayuda por campo, secciones numeradas, JavaScript.

## Decisions

**Firma del contrato C6.** `{% include "_campo.html" with campo=form.x prefijo="$" %}` (`prefijo` opcional, texto del `input-group`)
y los filtros `control` y `es_casilla` (`{% load formularios %}`). `_opciones.html` recibe `campo=` y se usa para `RadioSelect`.
No cambia ninguna firma de C0 a C5.

**Los filtros viven en `apps/core/templatetags/formularios.py`, no en `condohub.py`.** #76 y #77 agregarán filtros (montos, RUT) a
`condohub.py`; si C6 también lo editara, tres PR chocarían en el mismo archivo. Un módulo aparte aísla el contrato.
`{% load formularios %}` no choca con el módulo Python `apps/core/formularios.py` (son espacios de nombres distintos).
Alternativa descartada: ampliar `condohub.py` (menos archivos, pero conflictos seguros entre #75, #76 y #77).

**`control` es idempotente y manda sobre `BootstrapMixin`.** Quita del `class` existente `form-control`, `form-select` y `form-check-input`
y pone la correcta según el widget (hoy el mixin deja `form-control` en `RadioSelect`, que es incorrecto). Así funciona igual con formularios
que no heredan del mixin (p. ej. los de autenticación de Django). Con error agrega `is-invalid`, `aria-invalid="true"` y `aria-describedby`
(`<id>_helptext` si hay ayuda, `<id>_error`). Sin error no agrega `aria-invalid`; con ayuda y sin error deja `aria-describedby="<id>_helptext"`.
Django 5.2 ya agrega algunos de estos atributos solo; el filtro los fusiona sin duplicar (se verifica con una prueba sobre el HTML real).

**«Seleccione…» se aplica en `BootstrapMixin` (`rotular_vacios`), no en el filtro ni en la plantilla.** Las opciones salen de
`field.choices` / `empty_label` al crear el formulario; un filtro de plantilla no debería mutar el campo. El mixin ya recorre todos los
campos, así que cubre todos los formularios que lo usan sin editarlos. Reemplaza solo el texto `---------`: los `empty_label` propios
(«Sin proveedor», «Todos los edificios») y `empty_label=None` se conservan. Alternativa descartada: pasarlo campo por campo (15 formularios).

**Casillas y campos a mano.** `es_casilla` equivale a la condición actual (`widget.input_type == "checkbox"`), por lo que las casillas de
`_formulario.html` siguen con `form-check`. `gastos/reporte.html` pasa a `_campo.html` (filtros en fila, sin cambiar los nombres de los campos GET).
`importar.html` no se toca: su casilla no es un campo de Django. `CheckboxSelectMultiple` y `RadioSelect` usan `_opciones.html`; `_campo.html`
delega en él con `{% include %}`, así que `_formulario.html` no necesita saber qué widget es.

**Errores con `invalid-feedback d-block`.** `d-block` siempre, porque en `input-group` y en grupos de opciones el error no es hermano del
control con `is-invalid` y Bootstrap lo ocultaría. Se mantiene el color de texto de error de hoy.

**CSS.** `.form-control::placeholder { color: #6c757d; opacity: 1; }` (4,6:1 sobre blanco, AA) y `.subtitulo-seccion` (línea superior, sin tarjeta), usando las variables de CondoHub.

## Risks / Trade-offs

- **Cambio visual en 15 formularios a la vez** → Mitigación: una prueba que carga cada página de formulario (200) y las pruebas actuales sin tocar.
- **Conflictos con ramas de Maximiliano y Winderson** (editan plantillas de formulario) → Mitigación: `_formulario.html` conserva su firma, así que sus plantillas no cambian; se avisa en el grupo al unir.
- **Atributos ARIA duplicados con Django 5.2** → Mitigación: fusionar en el filtro y probar el HTML.
- **Selects con valor inicial** pierden «Seleccione…» si el campo es opcional con opción vacía propia → es el comportamiento buscado.

## Migration Plan

Sin migraciones. Orden: filtros y mixin, componentes, `_formulario.html`, CSS, `reporte.html`. Rollback: revertir el PR. Al unir, avisar en el grupo y pedir que actualicen sus ramas.
