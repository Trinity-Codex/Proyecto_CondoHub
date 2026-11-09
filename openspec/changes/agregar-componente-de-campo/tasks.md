# Tasks

Cambio transversal del Issue #75 (`Closes #75`). Contrato C6 para #76, #77 y #78.

## 1. Filtros y selects

- [x] 1.1 Crear `apps/core/templatetags/formularios.py` con `control` y `es_casilla` (clase correcta según widget sin duplicar las de `BootstrapMixin`; con error, `is-invalid`, `aria-invalid="true"` y `aria-describedby`). Verificación: pruebas en `apps/core/tests.py` para campo con error, sin error, con y sin ayuda, y widget de tipo select, casilla y radio.
- [x] 1.2 Agregar `rotular_vacios` a `BootstrapMixin` en `apps/core/formularios.py`: cambia `---------` por «Seleccione…» en `ChoiceField` y `ModelChoiceField`, y respeta `empty_label` propios y `None`. Verificación: prueba con un select sin texto propio, con «Sin proveedor» y con `empty_label=None`.

## 2. Plantillas y CSS

- [x] 2.1 Crear `templates/_campo.html` (con `prefijo` opcional, asterisco `aria-hidden`, ayuda con id `_helptext`, errores `invalid-feedback d-block` con id `_error`) y `templates/_opciones.html` (fieldset + legend). Verificación: prueba que renderiza `aria-describedby="<id>_helptext <id>_error"` con error y sin `aria-invalid` sin error.
- [x] 2.2 Reescribir `templates/_formulario.html` para incluir `_campo.html` en el bucle, conservando errores generales y campos ocultos. Verificación: `python manage.py test apps` sin tocar las pruebas actuales.
- [x] 2.3 CSS en `static/css/condohub.css`: placeholder `#6c757d` con `opacity: 1` y `.subtitulo-seccion`. Verificación: medir el contraste del placeholder (≥ 4,5:1) y revisar a 375 px.
- [x] 2.4 Pasar `gastos/reporte.html` a `_campo.html` conservando los nombres GET. Verificación: la prueba del reporte con filtros sigue en verde.

## 3. Pruebas y cierre

- [x] 3.1 Prueba que cada página de formulario de las 15 plantillas que incluyen `_formulario.html` responde 200 con su rol permitido y 403 o redirección con uno no permitido. Verificación: `python manage.py test apps` completo.
- [x] 3.2 Prueba de que un POST sin JavaScript se guarda igual que antes (un formulario representativo).
- [x] 3.3 Documentar C6 en `docs/equipo/PLAN_PMV_27NOV.md` (tabla de contratos) y en `docs/GUIA_NUEVA_FEATURE.md`. Verificación: `openspec validate --all --strict`.
- [ ] 3.4 Archivar el cambio en el mismo PR (`/opsx:archive`) y avisar en el grupo la firma C6.
