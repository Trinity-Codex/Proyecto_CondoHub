# Tasks

## 1. Cálculo (apps/gastos/proyeccion.py)

- [x] 1.1 Base mensual del año base desde los períodos emitidos, con relleno por promedio y marca de estimado; verificar con pruebas que los ítems de cobro y los períodos abiertos no cuentan.
- [x] 1.2 Fórmula con IPC y crecimiento compuestos y redondeo único; verificar con cifras sencillas (100.000 → 110.000 → 121.000).
- [x] 1.3 Reparto por unidad con la estrategia y el % del fondo vigentes; verificar que el total de cada mes es igual a la suma por unidad con montos que no se dividen exacto.

## 2. Vistas y plantillas

- [x] 2.1 Formulario GET de parámetros con rangos; verificar que valores inválidos no dan 500.
- [x] 2.2 Vista de la proyección con cuadro de supuestos, tabla por mes y tabla por unidad; `RolRequeridoMixin` (administrador y comité) y datos del condominio activo; verificar 403 para residente y conserje y aislamiento.
- [x] 2.3 CSV con `respuesta_csv` desde el mismo cálculo; verificar que coincide con la pantalla.
- [x] 2.4 Enlace desde la lista de períodos; revisar la UI a 1440×900 y 375×812.

## 3. Pruebas

- [x] 3.1 Pruebas en `apps/gastos/tests_proyeccion.py`; `python manage.py test apps` completo y `openspec validate --all --strict`.

## Workflow follow-up

- `/code-review high` antes de abrir el PR.
- Archivar el cambio cuando el cliente valide el cálculo (el PR usa Refs #121).
