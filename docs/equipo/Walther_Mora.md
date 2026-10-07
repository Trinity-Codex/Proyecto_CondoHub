# Walther Mora — Tareas y coordinación

Plan general del equipo: [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).

**Tu área:** gastos comunes (app nueva `apps/gastos/`). Es la **ruta crítica** del proyecto:
Winderson depende de tu modelo `DetalleGastoComun` el jueves y tus reportes dependen de sus pagos
el viernes. Además coordinas la integración y la entrega del sábado.

Tu entorno ya está listo (MySQL con la base `condohub`, `.env` y datos demo). Si alguna vez necesitas
rehacerlo, sigue la Parte 1 de la guía de [Maximiliano](Maximiliano_Soto.md) o de
[Winderson](Winderson_Castrillo.md).

---

## Tus tareas

| Día | Issue | Tarea | Rama sugerida |
|---|---|---|---|
| **Miércoles 7** | [#1](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/1) | Registrar los egresos del mes (RF02) | `feature/1-egresos` |
| **Jueves 8 (temprano)** | #2 (parte 1) | **PR corto: solo el modelo `DetalleGastoComun`** | `feature/2-modelo-detalle` |
| **Jueves 8** | [#2](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/2) | Calcular y emitir gastos comunes: Strategy + fondo de reserva (RF02) | `feature/2-calculo-emision` |
| **Viernes 9 (tarde)** | [#5](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues/5) | Reporte de gastos comunes y morosidad (RF11) | `feature/5-reportes` |
| **Sábado 10** | — | Integración, datos demo, documentación y entrega | — |

Tus PR los revisa **Maximiliano**; tú revisas los de **Winderson**.

### #1 — Egresos del mes (miércoles)

**Dónde:** app nueva `apps/gastos/` (sigue la [guía de nuevos módulos](../GUIA_NUEVA_FEATURE.md)).

1. `PeriodoGasto`: `condominio`, `anio`, `mes`, `estado` (ABIERTO / EMITIDO), único por
   (condominio, anio, mes). Agrega también `porcentaje_fondo_reserva` (por defecto 5, mínimo 5):
   así el fondo de reserva queda en tu app y no hay que tocar `Condominio`.
2. `Egreso`: `periodo`, `categoria` (TextChoices: remuneraciones, consumos básicos, mantención,
   aseo, seguridad, administración, otros), `descripcion`, `monto` (entero positivo), `fecha`.
   **Sin** campo proveedor: lo agrega Winderson el viernes (#9).
3. Vistas: lista de períodos, detalle con sus egresos y total, crear/editar/eliminar egresos
   solo si el período está ABIERTO. Administrador edita; comité solo ve.
4. Enlace **"Gastos comunes"** en el menú para `es_admin or es_comite`.

El comprobante adjunto del Issue puede quedar para la fase 2 (necesita configurar archivos subidos, como #15).

### #2 — Cálculo y emisión (jueves)

**Primero (antes de las 10:00):** PR corto con **solo** el modelo `DetalleGastoComun` tal cual el
[contrato del plan](PLAN_DE_TRABAJO.md#contrato-del-modelo-detallegastocomun-walther-lo-crea-winderson-lo-usa)
y su migración. Pídele a Maximiliano que lo revise de inmediato y únelo: Winderson empieza #3 con él.

Después, el cálculo:

1. **Patrón Strategy** en `apps/gastos/prorrateo.py`: clase base `EstrategiaProrrateo` con
   `calcular(total, unidades) -> dict[unidad, monto]` y estrategias `PorAlicuota` (por defecto) y
   `PartesIguales`. Es el patrón que el Informe 2 eligió para esto (sección 5.3).
2. **Redondeo sin perder pesos (método del resto mayor):** calcula cada parte con `Decimal`, toma
   la parte entera y reparte los pesos que sobran a las unidades con mayor decimal. La suma debe
   ser **exactamente** el total (incluye una prueba con 3 unidades y un total que no divida exacto).
3. **Emitir:** valida que las alícuotas sumen 1 (`Condominio.suma_alicuotas()`), crea un
   `DetalleGastoComun` por unidad con `monto` y `monto_fondo_reserva`, pasa el período a EMITIDO
   (todo en `transaction.atomic()`) y notifica a los residentes con el **patrón Observer**
   (`PeriodoGasto` hereda de `Sujeto`; suscríbelo en `apps/notificaciones/apps.py`).

### #5 — Reporte de gastos comunes y morosidad (viernes en la tarde)

Necesita los pagos de Winderson (#4), que él une el viernes antes del almuerzo.

1. Por período: total emitido, total pagado (`Sum` de `pagos__monto`), % de recaudación y unidades morosas.
2. Filtros por edificio y período. Visible para administrador y comité.
3. Exportar a CSV para Excel: `HttpResponse(content_type="text/csv")`, separador `;` y escribir
   primero el BOM (`"﻿"`) para que Excel lea bien las tildes.

---

## Coordinación

### Durante la semana

- Dirige la **reunión diaria de 15 minutos** (Scrum Master del Informe 2).
- Vigila el tablero: si #2 se atrasa, el reporte (#5) pasa al sábado en la mañana (holgura).
- Une los PR solo con la aprobación del revisor y el CI en verde. Como administrador de la
  organización GitHub te deja saltarte la protección: **no lo hagas** salvo una emergencia.

### Sábado 10: integración y entrega

| Hora (aprox.) | Tú |
|---|---|
| Mañana | Revisar el tablero: unir lo pendiente o decidir qué pasa a la fase 2 |
| 14:00 – 17:00 | Extender `cargar_demo` (cada uno agrega su método `_demo_<modulo>()`) y emitir un período demo; probar todos los flujos con cada rol |
| 17:00 – 19:00 | Actualizar README y la tabla de trazabilidad de [DOCUMENTACION.md](../../DOCUMENTACION.md) (sección 7) con los RF terminados |
| **19:00** | Congelamiento: solo correcciones críticas |
| **20:00** | Entrega: verificar que el CI de `main` esté en verde y que el README muestre todo |

## Lista diaria

- [ ] `git checkout main` y `git pull` al empezar el día; `python manage.py migrate`.
- [ ] Reunión diaria de 15 minutos.
- [ ] Revisar los PR de **Winderson** el mismo día.
- [ ] Revisar el tablero: nadie bloqueado más de 30 minutos.
