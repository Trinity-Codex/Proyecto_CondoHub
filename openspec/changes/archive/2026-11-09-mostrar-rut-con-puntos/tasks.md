# Tasks

Cambio transversal del Issue #77 (`Closes #77`). Usa C6 (#75) y el registro de #76. Sin migraciones.

## 1. Funciones puras de RUT

- [x] 1.1 Mover `normalizar_rut` y `calcular_dv` a `apps/core/formato.py`, agregar `RUT_FORMATO` y `formatear_rut`, y hacer que `apps/cuentas/validadores.py` los reexporte (`__all__`) y use `RUT_FORMATO` en `validar_rut`. Verificación: las pruebas actuales de `cuentas` pasan sin tocarlas; prueba parametrizada en `apps/core/tests.py`: `12345678-5`→`12.345.678-5`, `1234567-4`→`1.234.567-4`, `96511790-k`→`96.511.790-K`, `abc`, `123456785`, `""` y `None` sin cambio; `apps.core` no importa `apps.cuentas` (prueba que lee el código fuente).
- [x] 1.2 Filtro `|rut` en `apps/core/templatetags/condohub.py` (`None` y `""` → `""`). Verificación: prueba de plantilla con `{{ v|rut|default:"—" }}`.

## 2. Campo, widget y aviso

- [x] 2.1 `RutInput` y `RutField` en `apps/core/campos.py` según design.md. Verificación: pruebas de entradas válidas e inválidas, `cleaned_data` normalizado, vacío opcional y obligatorio, mensajes iguales a los actuales, `format_value` con puntos y texto inválido tal cual, placeholder válido (su DV cuadra).
- [x] 2.2 `_campo.html` y filtro `control`: región `<id>_aviso` y `aria-describedby` solo con `aviso_vivo`. Verificación: prueba de orden de ids con y sin error; un campo de texto común y los de C6 salen idénticos.

## 3. Formularios y listados

- [x] 3.1 `apps/cuentas/forms.py`: `FormularioAltaUsuario.rut = RutField(...)` y `field_classes = {"rut": RutField}` en `FormularioPerfil`. Verificación en `apps/cuentas/tests.py`: alta y perfil con «12.345.678-5» y «12345678-5» guardan `12345678-5`; RUT ajeno rechazado como hoy; propio aceptado; perfil con el RUT vacío sigue válido.
- [x] 3.2 `apps/proveedores/forms.py`: `field_classes = {"rut": RutField}`; `Proveedor.__str__` con `formatear_rut` (revisar antes con grep las pruebas que comparan el texto). Verificación en `apps/proveedores/tests.py`: duplicado con y sin puntos rechazado; la edición muestra «76.086.428-5».
- [x] 3.3 Aplicar `|rut` en `cuentas/usuarios.html` y `proveedores/lista.html`, y mostrar el RUT del residente en `unidades.html` solo con `es_admin`. Verificación: pruebas de listados (administrador ve puntos; comité ve proveedores con puntos y Unidades sin RUT; residente 403).

## 4. JavaScript progresivo

- [x] 4.1 Agregar `rut` a `FORMATOS` en `static/js/formato.js` (`formatearRut`, `rutValido`, `calcularDv`, aviso en `[data-rut-aviso]`, error en `focusout`, `rutManual`). Verificación en el navegador con `javascript_tool`: «123456785»→«12.345.678-5» con cursor correcto; «1234567-4», «96511790k», borrar en medio, pegar «12.345.678-5» y «12345678 5»; letra, coma, K en medio y 10 dígitos no se tocan; «RUT válido.» desde 8 caracteres; error solo al salir; `aria-invalid` se limpia al escribir; sin errores en la consola. Casos anotados en el PR.
- [x] 4.2 Verificar sin JavaScript que alta, perfil y proveedor guardan normalizado, y a 375 px que nada desborda. Verificación: captura de confirmación.

## 5. Cierre

- [x] 5.1 Actualizar `docs/GUIA_NUEVA_FEATURE.md` (usar `RutField` y `|rut`) y la nota de C6 en `docs/equipo/PLAN_PMV_27NOV.md`. Verificación: `python manage.py test apps`, `python manage.py makemigrations --check` y `openspec validate --all --strict`.

## Workflow follow-up

- `/code-review high` antes de unir; archivar con `/opsx:archive` en el mismo PR.
- Avisar en el grupo a Maximiliano (`unidades.html`, `usuarios.html`) y Winderson (`proveedores`) qué líneas cambiaron.
