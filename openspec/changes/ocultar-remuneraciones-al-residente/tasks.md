## 1. Función única

- [x] 1.1 Crear `egresos_para_residente(periodo)` en `apps/pagos/consultas.py`, documentada para #6 y #55.

## 2. Pantallas del residente

- [x] 2.1 Revisar los lugares de `apps/pagos` donde el residente ve egresos: solo el detalle del cobro; el estado de cuenta no los lista y no hay PDF ni exportación.
- [x] 2.2 `CobroDetailView` y `pagos/detalle.html` usan la función.

## 3. Pruebas

- [x] 3.1 En `apps/pagos/tests.py`: sin sueldos ni descripciones libres, línea agrupada, subtotales que cuadran, aislamiento entre condominios, filtro de residencia (#46), 403 del residente y 200 de administrador y comité en `gastos:periodo_detalle`.
