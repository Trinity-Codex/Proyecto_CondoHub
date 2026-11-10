# Design

## Context

Ver `proposal.md` para el motivo. En `main` (`64bd63b`), `PeriodoGasto` guarda porcentaje y fecha de emisión; `DetalleGastoComun` guarda el aporte individual redondeado. `emitir_periodo(periodo)` bloquea el período con `select_for_update()` y guarda cobros, estado y notificaciones dentro de `transaction.atomic()`. Lo llaman la vista, la demo y pruebas de gastos, pagos y notificaciones. No hay libro del fondo ni evento de emisión. C1 ofrece `registrar(..., *, antes=None, despues=None)` y acepta `usuario=None` para «Sistema».

## Goals / Non-Goals

**Goals:** entregar C5 estable para #55, conservar prorrateo y atomicidad, aislar condominios y auditar cambios monetarios.

**Non-Goals:** almacenar un saldo duplicado, reconstruir egresos desconocidos, determinar efectivo bancario o editar apps de otros dueños. Este cambio referencia acuerdos; no los tramita.

## Decisions

### 1. Libro de movimientos en gastos

`MovimientoFondo` vive en `apps/gastos/models.py`: `condominio`, `tipo` (`INICIAL`, `INGRESO`, `EGRESO`, `AJUSTE`), `monto` firmado, `fecha` contable, `descripcion`, `acuerdo`, `proveedor` opcional, `periodo` opcional, `creado_por` opcional para Sistema y fecha de creación. El proveedor usa `SET_NULL`, conservando el movimiento; el período, `RESTRICT`: impide borrar un período conservando sus movimientos, pero permite borrar el condominio completo cuando ambos se eliminan en cascada, como requiere el reinicio de la demo. Ningún saldo se agrega a `Condominio`.

`monto` es `BigIntegerField` en pesos enteros: inicial e ingreso no negativos, egreso negativo, ajuste no nulo. Un ingreso tiene período obligatorio; los demás tipos no lo tienen. Solo un inicial por condominio y un ingreso por período. MySQL no admite índices únicos parciales: para el inicial, columna auxiliar nullable `marca_inicial` fija a 1 solo en `INICIAL`, restricción de consistencia y `UniqueConstraint(condominio, marca_inicial)`; para ingresos, unicidad del período nullable. No usar `UniqueConstraint(condition=...)`.

El egreso se ingresa positivo con `MontoField`; el servicio guarda su negativo. Los movimientos son inmutables en el producto y no se habilita edición/borrado desde Django Admin. Una corrección agrega un ajuste con signo, motivo y referencia obligatorios. Se permite saldo contable negativo y se muestra explícitamente: #8 no valida disponibilidad bancaria.

Alternativas: un saldo editable duplica la fuente de verdad; sumar solo los detalles no representa egresos ni ajustes. No se crea un servicio contable genérico.

### 2. Contrato C5 propuesto

Firmas públicas en `apps/gastos/fondo.py`:

```python
saldo_fondo(condominio, hasta_periodo=None) -> int
movimientos_fondo(condominio, periodo=None) -> QuerySet[MovimientoFondo]
```

Entradas: instancias guardadas de condominio y período. Un período ajeno provoca `ValidationError` antes de consultar importes. Las vistas convierten identificadores ajenos en 404 con el queryset del condominio. Las funciones no reciben solicitudes ni aplican roles; son de solo lectura.

- `saldo_fondo(..., None)`: suma de todos los movimientos del condominio, sin corte implícito por hoy, convertida a `int`.
- `hasta_periodo`: corte inclusivo al último día calendario de `anio/mes`. Incluye el ingreso emitido de ese período y todos los movimientos con `fecha` hasta ese día. No exige EMITIDO para consultar: un período abierto todavía no aporta ingresos.
- El ingreso lleva fecha contable del último día del mes del período, aunque la emisión ocurra después. No se corta por `fecha_emision` ni por fecha de creación. Los manuales usan la fecha declarada por el administrador.
- `movimientos_fondo(..., None)`: todos los movimientos. Con `periodo`: únicamente fechas entre el primer y último día de ese mes, ambos incluidos, orden `fecha, pk`. Sus objetos exponen `pk`, `tipo`, `monto` firmado, `fecha`, `descripcion`, `acuerdo`, `proveedor` y `periodo`; cargar las relaciones evita una consulta por fila.
- Sin movimientos ni legado pendiente: entero `0` y queryset vacío. Con legado, rigen los errores de cobertura de la decisión 3.

Ejemplo ficticio: inicial $100.000, aporte de noviembre $5.000 emitido en diciembre, egreso de noviembre $2.000 y egreso de diciembre $1.000. El corte de noviembre devuelve $103.000 y su listado solo incluye movimientos de noviembre. #55 suma ingresos/egresos del queryset y muestra el saldo al mismo corte en su propio Issue. Un movimiento retroactivo posterior modifica el resultado histórico: no se prometen informes congelados.

### 3. Legado y apertura: decisión aprobada por Walther

La única migración nueva de `gastos` crea estructura y restricciones; **no genera ingresos de períodos ya emitidos**. Se evita sumar aportes históricos a un inicial que ya los incluye. No modifica cobros ni inventa egresos.

El administrador configura el movimiento inicial desde el fondo, con monto, fecha y descripción del respaldo. Con legado, la fecha de apertura es como mínimo el primer día del mes siguiente al último período emitido sin movimiento; el inicial incluye el resultado contable de todos esos períodos. Debe conciliarse con antecedentes externos y aportes cobrados; no confundirse con efectivo recaudado.

C5 detecta legado mediante períodos emitidos sin ingreso asociado. Si falta inicial, ambas funciones lanzan `ValidationError` con código `fondo_sin_apertura`. Con inicial, una consulta de corte/mes anterior a su fecha lanza `ValidationError`, código `fondo_sin_cobertura`; #55 presenta «Histórico del fondo no disponible». No se devuelve cero como historia desconocida. Después de abrir, la consulta sin período incluye todo el libro registrado.

La pantalla muestra el aviso y permite configurar al administrador aunque el saldo esté pendiente. No admite movimientos manuales ni nuevas emisiones con fecha contable anterior a la apertura; valida antes de guardar. Sin legado, el inicial es opcional; si se agrega después, su fecha no puede superar la del primer movimiento existente. Las reglas viven en `fondo.py`, sin editar `apps/condominios`.

Alternativa: generar una vez ingresos históricos desde los detalles. Permite ver aportes, pero sin egresos no reconstruye saldo y exige redefinir apertura para evitar doble conteo. Cambiar la recomendación requiere revisar escenarios y tareas antes de aplicar.

### 4. Emisión y C1

Ampliar a `emitir_periodo(periodo, *, usuario=None)`, manteniendo válidas las llamadas actuales. La vista pasa `request.user`; demo y pruebas existentes conservan Sistema. Dentro de su transacción: validar apertura/corte, crear detalles, sumar sus `monto_fondo_reserva` persistidos, crear el ingreso, cerrar, registrar y notificar como hoy. Mantener bloqueo y unicidad, incluso con aporte cero. No recalcular porcentaje para el movimiento ni generar otro ingreso al recibir pagos.

Usar acciones existentes: `Accion.MODIFICAR` sobre `PeriodoGasto` para emisión y `Accion.CREAR` sobre el ingreso y los manuales, con tipo, monto, fechas y referencias. El evento de emisión incluye estado anterior/posterior y aporte total. Cada `registrar` comparte la transacción: si falla, no se guarda nada. No agregar constantes ni editar `apps/auditoria`.

Los servicios de inicial, egreso y ajuste validan monto, campos obligatorios y pertenencia de proveedor/período; el formulario no es la única barrera. Bloquear la fila de condominio durante creación manual y tomar ese bloqueo antes del período en emisión, siempre en ese orden, evita carreras entre apertura y emisión. Solo se lee/bloquea `Condominio`, sin modificar su modelo.

### 5. Pantalla, permisos y demo

Rutas en `apps/gastos`: listado, detalle de movimiento y creación de inicial, egreso y ajuste; enlace desde `gastos/periodos.html`. Toda vista nueva usa `RolRequeridoMixin` y `CondominioQuerysetMixin`; la creación asigna condominio/autor desde la solicitud y filtra proveedores. Consulta para administrador y comité; formularios solo administrador. Proteger GET y POST. No agregar filtros al PMV; si se incorpora alguno, usar `FiltrosGetMixin`.

Reutilizar `_formulario.html`/`_campo.html`, `MontoField`, `{{ valor|pesos }}` y `.insignia-recibido`/`.insignia-con-deuda` con texto «Ingreso»/«Egreso» y tipos explícitos para inicial/ajuste. Listado paginado y detalle legible en móvil. No mostrar RUT, residentes ni unidades: #46 no aplica.

En `apps/gastos/demo.py`: inicial ficticio anterior a sus períodos, ingresos producidos por las tres emisiones y egreso ficticio con proveedor y acuerdo de ejemplo. Conservar claves `datos["periodos"]`; ampliar `huella_demo` y `HUELLA` en `apps/core/tests.py` para contar movimientos y sumas por tipo. No modificar el cargador común.

## Risks / Trade-offs

- Legado incompleto → apertura documentada y errores de cobertura en C5; limitación aprobada y expuesta mediante errores de cobertura para #55.
- Aportes emitidos impagos → rotular «Saldo contable del fondo»; no prometer caja ni registrar pagos otra vez.
- Fechas retroactivas → auditoría y corte contable explícitos; rendición congelada fuera del alcance.
- Pérdida de trazabilidad o cruce de condominio → inmutabilidad, validación en servicio/formulario, 403/404 y pruebas de rollback.
- Respaldo insuficiente → referencia obligatoria del acuerdo. El artículo 39 distingue autorizaciones; el producto conserva lo declarado, sin certificar su validez. Fuente: [BCN, Ley 21.442, artículo 39](https://www.leychile.cl/leychile/navegar?idNorma=1174663&idParte=10326480).

## Migration Plan

Con las decisiones aprobadas: respaldo según proceso del proyecto, una migración nueva de `gastos`, pruebas en base limpia y con períodos emitidos, y apertura manual del legado. La verificación y la regresión de reinicio se ejecutan en la base de pruebas; no se reinicia la base de desarrollo. Para revertir, retirar primero la interfaz; no deshacer migración ni borrar movimientos sin respaldo y decisión expresa de Walther.

## Decisiones aprobadas

Walther aprobó expresamente el 10 de noviembre de 2026 las tres recomendaciones y autorizó implementar, verificar, archivar y publicar el PR #92 sin unirlo:

1. No generar ingresos históricos en la migración. Apertura documentada y errores `fondo_sin_apertura` / `fondo_sin_cobertura` para #55.
2. Corte inclusivo al último día del mes. El aporte corresponde al mes del período aunque se emita después.
3. Inicial configurado por administrador con monto respaldado y fecha posterior al último período legado, según la regla de apertura de la decisión 3. Saldo contable distinto de efectivo recaudado.

No hay decisiones de diseño pendientes. Los montos reales de apertura los declara el administrador con su respaldo; la demo usa cifras ficticias.

## Excepción puntual de pruebas autorizada

Walther autorizó el 10 de noviembre de 2026 actualizar únicamente el fixture de `apps/pagos/tests.py::EstadoCuentaTest.test_la_notificacion_de_emision_lleva_al_estado_de_cuenta`: apertura ficticia de $0 al 01-11-2026 antes de emitir noviembre, pues su escenario tiene agosto–octubre legados. No se cambia código funcional de pagos ni sus expectativas.
