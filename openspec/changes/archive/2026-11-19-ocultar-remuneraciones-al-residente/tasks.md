## 1. Función única

- [x] 1.1 Crear `egresos_para_residente(periodo)` en `apps/pagos/consultas.py`, documentada para #6 y #55.

## 2. Pantallas del residente

- [x] 2.1 Revisar los lugares de `apps/pagos` donde el residente ve egresos: solo el detalle del cobro; el estado de cuenta no los lista y no hay PDF ni exportación.
- [x] 2.2 `CobroDetailView` y `pagos/detalle.html` usan la función.

## 3. Pruebas

- [x] 3.1 En `apps/pagos/tests.py`: sin sueldos ni descripciones libres, línea agrupada, subtotales que cuadran, aislamiento entre condominios, filtro de residencia (#46), 403 del residente y 200 de administrador y comité en `gastos:periodo_detalle`.

## 4. Correcciones de la revisión

- [x] 4.1 Categoría fuera de las opciones: se muestra el valor crudo en vez de dar 500.
- [x] 4.2 La etiqueta de remuneraciones se indexa por `.value` del enum.
- [x] 4.3 `total_egresos` de la vista es la suma de los subtotales mostrados (una consulta menos).
- [x] 4.4 Pruebas de fila completa, de categoría desconocida y del período con solo remuneraciones (riesgo aceptado en design.md).
