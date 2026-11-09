# Tasks

## 1. Base común

- [ ] 1.1 Crear `apps/core/listados.py` con `leer_opcion`, `armar_chips` y `FiltrosGetMixin` (`parametros_filtro`, `filtros_url`, `hay_filtros`, `q` reservado), y `templates/_chips.html`. Verificación: pruebas unitarias del helper (valor desconocido, `page` eliminado, otros parámetros conservados).
- [ ] 1.2 En `condohub.css`: `.chip` y `.chip-<estado>` con `--estado-*`, `.insignia` y `.insignia-<estado>`, `--estado-resuelto*` y `.table-responsive { position: relative; }`. Verificación: script que calcula los pares y confirma ≥4,5:1 el texto y ≥3:1 el borde.

## 2. Incidentes

- [ ] 2.1 `IncidenteListView`: usar el mixin, contar desde `get_queryset()` (una consulta), orden por urgencia y chips con `_chips.html`; quitar el `btn-group`. Verificación: pruebas de filtro, cantidades, aislamiento, residente (solo los suyos), orden y `assertNumQueries`.
- [ ] 2.2 `incidentes/_estado.html` con `.insignia-*`. Verificación: prueba de que el HTML trae la clase y el nombre del estado.

## 3. Reporte de recaudación

- [ ] 3.1 Crear `apps/gastos/filtros.py` (clave → `situacion`) y aplicar `situacion` en `ReporteMixin`, conservando `solo_deuda`, en la página y en el CSV. Verificación: pruebas de cada valor, valor inválido, CSV filtrado, 403 de residente y conserje, y totales sin cambio.
- [ ] 3.2 Chips con `Counter`, orden por urgencia solo en la página y `gastos/_situacion.html` con insignias. Verificación: pruebas de cantidades y orden.
- [ ] 3.3 `InicioView`: `?situacion=` en `_tarjetas_de_unidades` y quitar el `TODO(#80)`. Verificación: prueba de que cada tarjeta enlaza y su cantidad es igual a la del chip.

## 4. Egresos y unidades

- [ ] 4.1 `PeriodoDetailView`: `?categoria=` con chips (conteo junto al subtotal por categoría), orden `-fecha, -pk` y `gastos/_estado.html` con insignias. Verificación: pruebas de filtro, total intacto y 404 de período ajeno.
- [ ] 4.2 `UnidadesView`: `?ocupacion=`, chips y filtrado de unidades por edificio sin perder el `prefetch`. Verificación: pruebas de filtro, aislamiento y 403 de conserje y residente.

## 5. Proveedores y desborde

- [ ] 5.1 Confirmar la causa en `/proveedores/` a 375 px y medir con el DOM las tablas con `visually-hidden` (proveedores, período, cobranza, cuenta de unidad, estado de cuenta, reservas). Verificación: `scrollWidth <= clientWidth` en todas.

## 6. Verificación final del PR

- [ ] 6.1 Datos demo: confirmar que `cargar_demo` deja incidentes en los tres estados, unidades sin residentes, egresos de varias categorías y unidades al día, pendientes y morosas. Verificación: `python manage.py cargar_demo`.
- [ ] 6.2 Medir rectángulos (solapes, texto cortado, desborde) de los listados a 375 y 1440 px. Verificación: sin hallazgos; la captura solo confirma.
- [ ] 6.3 Ejecutar `python manage.py test apps`, `makemigrations --check` y `openspec validate --all --strict`. Verificación: todo pasa.
