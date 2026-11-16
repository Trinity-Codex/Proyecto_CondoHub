# QA de operación y finanzas · demo del cliente (#100)

Revisión del bloque **pagos, proveedores e incidentes** antes de la primera reunión con el cliente
(lunes 16-nov-2026). No reemplaza la prueba guiada formal (#59).

## Base usada

- Base **desechable y aislada**: `.demo_cliente/demo.sqlite3`, ignorada por git. Se creó con
  `python manage.py preparar_demo_cliente --settings=config.settings_demo`.
- Fecha de referencia de la demo: 16-nov-2026 (`DEMO_FECHA_REFERENCIA`).
- **Todos los datos son ficticios**: nombres, RUT, montos y correos `@condohub.cl` de prueba.
- Rama revisada: `main` (6eaa59e) más #97 (PR #104, pulido visual) y #98 (PR #103, datos ficticios).
- Solo se hicieron lecturas (GET). No se registraron pagos ni se cambiaron datos durante la revisión.
  La base de desarrollo no se tocó.

## 1. Matriz de rutas y roles

Código HTTP de cada GET. En las rutas con objeto, `propio/ajeno` indica el objeto del condominio
activo y el del otro condominio. **No hubo ningún 500.**

| Ruta | Admin @ Vista Verde | Admin @ Los Aromos | Comité @ VV | Conserje @ VV | Residente @ VV | Residente @ LA |
|---|---|---|---|---|---|---|
| `pagos:cobranza` | 200 | 200 | 200 | 403 | 403 | 403 |
| `pagos:estado_cuenta` (Mi cuenta) | 403 | 403 | 200 | 403 | 200 | 200 |
| `pagos:cuenta_unidad` | 200/404 | 200/404 | 200/404 | 403/403 | 403/403 | 403/403 |
| `pagos:registrar_pago` | 200/404 | 200/404 | 403/403 | 403/403 | 403/403 | 403/403 |
| `pagos:cobro_detalle` | 403/403 | 403/403 | 404/404 | 403/403 | 200/404 | 200/404 |
| `proveedores:lista` | 200 | 200 | 200 | 403 | 403 | 403 |
| `proveedores:nuevo` | 200 | 200 | 403 | 403 | 403 | 403 |
| `proveedores:editar` | 200/404 | 200/404 | 403/403 | 403/403 | 403/403 | 403/403 |
| `incidentes:lista` | 200 | 200 | 200 | 200 | 200 | 200 |
| `incidentes:nuevo` | 403 | 403 | 200 | 403 | 200 | 200 |
| `incidentes:detalle` | 200 | 404 ¹ | 200 | 200 | 200 | 404 ¹ |

¹ Los Aromos no tiene incidentes en la demo; el 404 es el de un identificador inexistente.

Lectura de la matriz:

- **Aislamiento entre condominios:** cualquier objeto del otro condominio responde 404 (o 403 si el
  rol ya no tiene acceso a la ruta). No se ven datos ajenos.
- **Registrar pago** es solo del administrador. El comité ve la cobranza y las cuentas, pero no registra.
- **Detalle del cobro** es la vista del residente: el administrador recibe 403 y el comité 404,
  como define la spec.
- **Nuevo incidente** lo reportan residentes y comité. El administrador recibe 403 a propósito:
  gestiona los incidentes, no los reporta.

## 2. Montos: pago, cuenta, reporte y fondo

Por cada período emitido se comparó el total recaudado del reporte de morosidad
(`generar_reporte`) con la suma de `pagado_del_cobro` (lo que muestran Mi cuenta y el detalle del
cobro) y con la suma directa de pagos en la base.

| Período | Emitido | Recaudado (reporte) | Σ pagado del cobro | Σ pagos en base | Ingresos al fondo | Monto ingresado | Aporte en cobros |
|---|---|---|---|---|---|---|---|
| Vista Verde 09/2026 | $2.320.001 | $1.948.801 | $1.948.801 | $1.948.801 | 1 | $110.476 | $110.476 |
| Vista Verde 10/2026 | $2.206.275 | $1.247.262 | $1.247.262 | $1.247.262 | 1 | $105.061 | $105.061 |
| Los Aromos 10/2026 | $712.425 | $416.213 | $416.213 | $416.213 | 1 | $33.925 | $33.925 |

- Las tres cifras de recaudación **cuadran** en cada período.
- El fondo de reserva tiene **un solo ingreso por período**, igual al aporte emitido. Registrar pagos
  no vuelve a sumar al fondo (`Pago.registrar` no crea movimientos).
- Saldos del fondo: Vista Verde $1.140.537 y Los Aromos $533.925 (lo verifican las pruebas de
  `apps/core/tests_demo_cliente.py`).

## 3. Ejemplos ficticios disponibles para mostrar

- **Pago total, parcial y pendiente** (Los Aromos 10/2026): o-101 y o-102 pagados, o-201 con un
  abono de $60.000 y o-202 pendiente. Vista Verde tiene cobros pagados y pendientes en sus dos
  períodos emitidos.
- **Proveedores activos:** 3 en Vista Verde y 2 en Los Aromos.
- **Incidentes en los tres estados** (Vista Verde): Recibido («Ampolleta quemada en pasillo piso 1»),
  En proceso («Portón de estacionamientos lento») y Resuelto («Basurero del hall con mal olor»).

## 4. Pantallas a 375 y 1440

Medido con **layout-inspector** (Chromium sin interfaz) a **375×812** y **1440×900**. Cada pantalla
se renderizó con el cliente de pruebas de Django, con sesión del rol que corresponde, sobre la base
aislada, y se cargó con el CSS real servido desde `runserver 127.0.0.1:8019`. El servidor se cerró
al terminar.

| Pantalla | Rol | 375 | 1440 |
|---|---|---|---|
| Cobranza | Admin (Los Aromos) | sin problemas | sin problemas |
| Cuenta de la unidad (o-201, abono parcial) | Admin | sin problemas | sin problemas |
| Registrar pago | Admin | sin problemas | sin problemas |
| Mi estado de cuenta | Residente (Los Aromos) | sin problemas | sin problemas ² |
| Detalle del cobro | Residente | sin problemas | sin problemas ² |
| Lista de proveedores | Admin (Vista Verde) | sin problemas ³ | sin problemas ² |
| Nuevo proveedor | Admin | sin problemas | sin problemas ² |
| Lista de incidentes | Admin | sin problemas ³ | sin problemas ² |
| Detalle de incidente (resuelto) | Admin | sin problemas ³ | sin problemas ² |
| Reportar incidente | Residente (Vista Verde) | sin problemas | sin problemas ² |

- **Sin scroll horizontal de página** en ninguna pantalla: `scrollWidth` igual al ancho de la ventana.
- **Controles:** todos miden 24 px o más (WCAG 2.2 AA, SC 2.5.8). Los campos de los formularios
  tienen su `label` asociado. Los errores y las ayudas de `_campo.html` van enlazados con
  `aria-describedby`.

² El único aviso es la campana de notificaciones con su contador encima: es intencional y está en
`templates/base.html`, fuera de este bloque.

³ Tres defectos de presentación que encontró la medición y que se corrigieron en #97 (PR #104):
- En el celular, las tablas de proveedores e incidentes dejaban los botones y el estado fuera de
  la vista, y había que desplazar la tabla para verlos.
- En el detalle de incidente, la fila de abajo pisaba la ruta (breadcrumb).

Después de corregirlos se midió de nuevo y ya no aparecen.

## 5. Qué no está terminado (decirlo con honestidad en la demo)

- **Anulación de pagos (#53):** propuesta en el PR #73, en **borrador** a la espera del OK de Walther
  sobre el contrato C4. No se muestra como terminada.
- **Avisos del pago solo a quien ve el cobro (#46):** PR #74, en **borrador**, a la espera del OK de
  Walther. Hoy el aviso de pago sigue el comportamiento de `main`.
- **Aviso de cobro en PDF (#6) y comprobante descargable (#56):** no están construidos. No se
  presentan como disponibles.
- Ninguno de estos puntos bloquea la demo: es una demo de percepción, no de cierre de alcance.

## 6. Secuencia breve para explicar la operación

1. **Administrador → Cobranza:** el estado de cada unidad del período, con sus insignias
   (pagado, pendiente) y el total adeudado.
2. **Cuenta de la unidad → Registrar pago:** el administrador anota un pago total o un abono.
   El saldo baja y el residente recibe un aviso.
3. **Residente → Mi cuenta → Detalle del cobro:** ve lo mismo que el administrador para su unidad,
   con montos que cuadran con la cobranza.
4. **Comité:** consulta la cobranza y los proveedores sin poder registrar ni editar.
5. **Proveedores:** la lista del condominio y su ficha (RUT con formato).
6. **Incidentes:** el residente reporta y el administrador ve el avance (recibido → en proceso → resuelto).

## Defectos encontrados

- De negocio: ninguno.
- De presentación: los tres de la sección 4, resueltos en #97 (PR #104).
- La revisión se hizo sobre una rama local que junta #97 y #98, sin unir. Después de unirlos a `main`
  conviene repetir la matriz en el ensayo integrado (#101).
