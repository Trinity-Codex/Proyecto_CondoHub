# Tasks

Cambio transversal del Issue #76 (`Closes #76`). Usa el contrato C6 (#75). Sin migraciones.

## 1. Formato en Python

- [x] 1.1 Crear `apps/core/formato.py` con `normalizar_monto` y `formatear_monto` según la gramática de design.md. Verificación: prueba parametrizada en `apps/core/tests.py`: «$ 1.250.000», «1250000», « 85.000 », «$1.250» → dígitos; «1,5», «1.5», «1500.5», «1.25.000», «0.500», «01.000», «-5», «abc», «1 250 000» → `None`; «0» → «0»; `formatear_monto` de 0, 1234567, -5000 y `None`.
- [x] 1.2 Prueba de la salida actual de `|pesos` (1234567, -5000, 1500.6, `None`, `""`, «abc») y luego pasar el filtro a `formatear_monto`. Verificación: la misma prueba en verde antes y después.

## 2. Campo y widget

- [x] 2.1 Crear `apps/core/campos.py` con `MontoInput` (`inputmode="numeric"`, `data-monto`, `prefijo = "$"`, `format_value`) y `MontoField` con `MENSAJE_MONTO_INVALIDO`. Verificación: pruebas del campo (entradas válidas e inválidas, vacío opcional y obligatorio, `min_value`) y del widget (entero y texto válido se formatean, texto inválido queda tal cual).
- [x] 2.2 En `templates/_campo.html`, tomar el prefijo con `{% firstof prefijo campo.field.widget.prefijo as prefijo_campo %}`. Verificación: prueba que un `MontoField` dibujado con `_formulario.html` lleva `input-group-text` «$» y que un campo de texto común no; las pruebas de C6 siguen en verde.

## 3. Formularios

- [x] 3.1 `apps/gastos/forms.py`: `field_classes = {"monto": MontoField}` en `EgresoForm`, quitar `monto` de `Meta.widgets`, placeholder «Ej.: 450.000» y `help_texts` «En pesos, con o sin puntos de miles.». Verificación en `apps/gastos/tests.py`: POST «1.250.000» guarda 1250000; «1.000.000.000» y las entradas de `test_montos_enteros_positivos` se rechazan; error en otro campo conserva «1.250.000»; editar un egreso de 450000 muestra «450.000».
- [x] 3.2 `apps/pagos/forms.py`: `monto = MontoField(label="Monto pagado", min_value=1)`. Verificación en `apps/pagos/tests.py`: POST «$ 85.000» registra 85000; sobre el saldo sigue rechazado; la página muestra el saldo inicial con puntos.
- [x] 3.3 `apps/reservas/forms.py`: `field_classes = {"tarifa": MontoField}` en `EspacioComunForm`. Verificación en `apps/reservas/tests.py`: «0» y «5.000» se guardan como 0 y 5000; «-1» se rechaza.
- [x] 3.4 Prueba de acceso: residente recibe 403 en el formulario de egreso, de pago y de espacio; el administrador ve 200 con `data-monto`. Verificación: `python manage.py test apps`.

## 4. JavaScript progresivo

- [x] 4.1 Crear `static/js/formato.js` (`reformatear`, `formatearMonto`, registro `FORMATOS` y listener delegado en `[data-monto]`) y cargarlo con `defer` en `templates/base.html` antes de `{% block scripts %}`. Verificación: en el navegador, escribir «1250000» muestra «1.250.000» con el cursor al final, editar en medio conserva la posición, «1,5» y «1500.5» no se modifican ni se reagrupan (marca en `dataset`); borrar al medio y pegar «$ 1.250.000» funcionan; `blur` formatea solo montos válidos; sin errores en la consola. Funciones puras probadas con `javascript_tool` y casos anotados en el PR.
- [x] 4.2 Verificar sin JavaScript (JS desactivado en el navegador) que el egreso con «1.250.000» se guarda, y medir a 375 px que el `input-group` no desborda. Verificación: captura de confirmación.

## 5. Cierre

- [x] 5.1 Actualizar `docs/GUIA_NUEVA_FEATURE.md` (Paso 3: cómo usar `MontoField`; C6: prefijo automático) y la nota de C6 en `docs/equipo/PLAN_PMV_27NOV.md`. Verificación: `openspec validate --all --strict` y `python manage.py makemigrations --check` sin cambios.

## Workflow follow-up

- `/code-review high` antes de unir; archivar con `/opsx:archive` en el mismo PR.
- Avisar en el grupo a Winderson (`apps/pagos/forms.py`) y Maximiliano (`apps/reservas/forms.py`) qué línea cambió.
