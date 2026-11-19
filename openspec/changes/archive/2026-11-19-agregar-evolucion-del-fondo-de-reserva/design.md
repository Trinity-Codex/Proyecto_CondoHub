# Design

## Context

El fondo ya es un libro contable (`MovimientoFondo`, #8) con saldo inicial, ingresos de emisión (fecha contable = último día del mes del período), egresos y ajustes, todos a nivel de condominio. El contrato C5 (`apps/gastos/fondo.py`) entrega `saldo_fondo(condominio, hasta_periodo)` y `movimientos_fondo`, y rechaza historia sin apertura (`fondo_sin_apertura`). El aporte de cada unidad está en `DetalleGastoComun.monto_fondo_reserva`; la suma de un período es exactamente el monto de su ingreso. El filtro de residencia (#46, contrato C2) es `apps.condominios.residencias.cobros_visibles`.

## Goals / Non-Goals

**Goals:**
- Una sola fuente de cálculo (módulo `apps/gastos/evolucion.py`) que alimentan las vistas, el gráfico y la tabla, para que muestren los mismos números.
- Solo lectura, sin migraciones, sin librerías nuevas y con pocas consultas (agregaciones en la base y reparto en Python).

**Non-Goals:**
- Fondos independientes por edificio, alícuotas históricas, exportar a CSV o PDF.

## Decisions

1. **Serie mensual desde el libro.** Se leen los movimientos del condominio una vez y se agrupan por mes contable, desde el mes del primer movimiento hasta el mes actual (o el último mes con movimientos, si es posterior). Por mes: apertura = cierre del mes anterior + saldo inicial del mes; luego aportes (ingresos), egresos, ajustes y cierre. El cierre de un mes es la suma de los movimientos con fecha hasta su último día, la misma regla de `saldo_fondo(condominio, hasta_periodo)`; las pruebas lo comparan mes a mes. Antes de calcular se llama a `validar_cobertura`: sin apertura en un condominio con legado, la vista muestra el aviso y no una serie. *Alternativa descartada:* llamar a `saldo_fondo` por mes (una consulta por mes).

2. **Meses sin período emitido.** Se marcan con `emitido = False`: la tabla dice «Sin período emitido» en la columna de aportes y la barra se dibuja con trama, pero su cierre sí refleja los egresos o ajustes reales de ese mes (no se inventa un aporte ni se omite un gasto).

3. **Saldo por edificio (consulta C4 pendiente).** Los egresos y ajustes se registran a nivel de condominio. El saldo de un edificio se define como la suma de los aportes de sus unidades más su parte de los demás movimientos (saldo inicial, egresos y ajustes), repartida según la suma de las alícuotas de sus unidades con `prorrateo.repartir` (resto mayor, sin perder pesos; los negativos se reparten por su valor absoluto y se les cambia el signo). Así los saldos de los edificios suman el saldo total. Se usan las alícuotas vigentes, no las de cada mes. Si el cliente espera fondos independientes por edificio (C4), este reparto se reemplaza por movimientos con edificio y cambia el modelo. Los aportes por edificio, mes a mes, son la suma de `monto_fondo_reserva` de sus unidades en los períodos emitidos.

4. **Los ítems de cobro (#117) no aportan al fondo.** Todas las sumas usan solo `monto_fondo_reserva`; nunca `monto_items`, `total` ni `LineaCobro`. Una prueba emite un período con ítems y verifica que los aportes no cambian.

5. **Aporte por residente.** Para el administrador y el comité se listan las residencias vigentes (las dadas de baja no, igual que en la pantalla de unidades, para no exponer a exresidentes) con el aporte de los meses que se superponen con su período, con la misma regla de superposición por mes que `cobros_visibles`; el cálculo se hace en Python sobre los cobros ya agregados, para no hacer una consulta por residente. Para el residente se usa `cobros_visibles` directamente (solo residencias activas), igual que «Mi cuenta».

6. **Acceso.** Evolución, edificios y aportes por unidad: `RolRequeridoMixin` con administrador y comité. Vista del residente: rol residente. Desglose de una unidad: la unidad se busca filtrada por el condominio activo (otra comunidad, 404); el administrador y el comité ven cualquiera; quien solo es residente necesita una residencia activa en esa unidad (si no, 403); el conserje, 403. Las rutas de consulta no cambian datos, así que no agregan eventos de auditoría ni rutas de escritura para la demo de Render.

7. **Gráfico.** SVG dibujado en la plantilla con geometría calculada en Python (alto proporcional al cierre, línea de cero para saldos negativos). `role="img"` con título y descripción, `<title>` por barra con el valor, y la tabla equivalente visible debajo con los mismos números. *Alternativa descartada:* Chart.js (dependencia externa, SRI y JavaScript para algo estático).

8. **Demo.** Se agregan tres meses emitidos y pagados antes de los existentes en Vista Verde, y la apertura se adelanta, para que el gráfico tenga seis meses. Cambia la huella de `cargar_demo` en `apps/core`, que se actualiza a propósito.

## Risks / Trade-offs

- [Alícuotas cambiadas después de emitir] → El saldo por edificio usa las alícuotas vigentes; se indica en la pantalla. Los aportes por edificio sí son exactos porque salen de los cobros guardados.
- [Condominio sin alícuotas (suma 0)] → El reparto da 0 a cada edificio y la pantalla avisa que el saldo por edificio no se puede calcular.
- [Más datos demo] → Cambian conteos de pruebas de demo en `apps/core`; se actualizan en este PR con comentario.

## Open Questions

- C3: si el residente debe ver más que su propio aporte. Hoy, solo el suyo.
- C4: si existen fondos independientes por edificio.
