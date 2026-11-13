## Context

Motivación y alcance: ver `proposal.md`. Requisitos: los deltas de `reportes` y `condominios`.

Lo que hay hoy y condiciona el diseño:

- Todo el sitio trabaja con **un** condominio activo (`request.condominio`, del middleware) y los roles de la
  membresía en él. `RolRequeridoMixin` redirige a «sin condominio» si no hay condominio activo y da 403 si falta
  el rol; `CondominioQuerysetMixin` filtra por ese único condominio.
- El reporte de recaudación se calcula en `apps/gastos/reportes.py` (`generar_reporte(periodo, edificio)`), y
  sus totales salen de las filas. `ReporteMixin` y las vistas `ReporteView` / `ReporteCsvView` toman el
  condominio de la sesión. `celda_segura` (neutraliza fórmulas) vive en `apps/gastos/views.py`.
- `apps/cartera` tiene solo la página provisional de C0 (administrador y comité) y un `demo.py` vacío.
- C1 está en `main`: `registrar(usuario, condominio, accion, objeto, *, antes=None, despues=None)`, con
  `Accion.CAMBIAR_ROL`. C4 (#53) aún no: `anotar_pagado` todavía cuenta los pagos anulados.
- Los datos demo tienen dos condominios, pero solo Vista Verde tiene períodos emitidos.

## Goals / Non-Goals

**Goals:** cifras de la cartera iguales a las del reporte sin un segundo cálculo; aislamiento demostrable entre
condominios asignados y no asignados; ningún cambio en `apps/condominios`, `apps/auditoria` ni `reportes.py`.

**Non-Goals:** dar al administrador general un condominio activo o un rol en la membresía; chips o filtros por
situación en la cartera; caché del cálculo.

## Decisions

**1. Modelo `AsignacionCartera(usuario, condominio, asignada_el)`, único por par, migración `cartera/0001`.**
Una persona es administrador general si tiene al menos una asignación a un condominio activo.
Alternativas: un rol nuevo en `Membresia` (cambia `apps/condominios`, de Maximiliano, y le daría condominio
activo y entrada a toda vista con `roles_permitidos = None`); un modelo con `ManyToMany` (los cambios por
`m2m_changed` no traen al usuario que los hizo); un grupo de Django (no se ata a condominios).

**2. Admin solo para el superusuario, con alta y baja, sin edición.** `AsignacionCarteraAdmin` responde
`is_superuser` en sus permisos; al editar, usuario y condominio son de solo lectura (cambiar de condominio es
quitar y asignar). La auditoría se registra en `save_model` (alta), `delete_model` y `delete_queryset` (baja,
antes de borrar), cada una en `transaction.atomic()`:
`registrar(request.user, asignacion.condominio, Accion.CAMBIAR_ROL, asignacion, antes={"administrador_general": None}, despues={"administrador_general": usuario.pk})`
y al revés en la baja. Se guarda el id de la persona, no su nombre ni RUT. No se agrega una constante a `Accion`
(es carpeta de Winderson). Alternativa: señales; no conocen al usuario de la petición.

**3. Permisos propios en `apps/cartera/permisos.py`, en lugar de `RolRequeridoMixin` y `CondominioQuerysetMixin`.**
Ninguno sirve tal cual: el primero exige un condominio activo y un rol en él (el administrador general no los
tiene) y el segundo filtra por un solo condominio. En su lugar:
- `condominios_de_cartera(usuario)`: condominios activos con asignación; el superusuario, todos los activos.
- `CarteraRequeridaMixin(LoginRequiredMixin)`: sin sesión lleva al inicio de sesión; sin condominios de
  cartera, 403.
- Toda consulta de la app parte de `condominios_de_cartera(request.user)`; una vista con `<pk>` usa
  `get_object_or_404(condominios_de_cartera(usuario), pk=pk)`, así un condominio no asignado da 404.

**4. Cifras: `apps/cartera/consolidado.py` llama a `generar_reporte` por condominio.** Para el mes elegido busca
el período emitido de cada condominio (una consulta para todos) y arma `FilaCartera(condominio, reporte)`; los
totales suman las filas y el % se calcula sobre los totales. No hay SQL nuevo ni cambio en `reportes.py`: cuando
C4 cambie `anotar_pagado`, la cartera cambia con el reporte. Una prueba compara cada fila con `generar_reporte`
y con la página del reporte.

**5. Mes elegido con `?mes=AAAA-MM`.** Las opciones son los meses con algún período emitido en los condominios
de la cartera, del más reciente al más antiguo; uno inválido se ignora. Formulario GET con `_campo.html`.
Alternativa: el último período de cada condominio, que mezclaría meses en los totales.

**6. Reporte de un condominio desde la cartera, sin cambiar el condominio activo.** En `apps/gastos/views.py`,
`ReporteMixin` se divide en una base sin permisos, que toma el condominio de `get_condominio_reporte()` (por
defecto, el de la sesión) y las URL de la página y del CSV desde atributos, y la versión actual con
`RolRequeridoMixin`. `apps/cartera` agrega `/cartera/<pk>/reporte/` y `/cartera/<pk>/reporte/csv/` con
`CarteraRequeridaMixin` y el condominio de la decisión 3. `gastos/reporte.html` recibe por contexto las migas y la
URL del CSV. Las pruebas actuales del reporte, sin cambios, prueban que su comportamiento se mantiene.
Alternativas: enlazar solo si la persona también es miembro (no sirve a la gerencia); dar al administrador
general un condominio activo (abre todas las vistas con `roles_permitidos = None`).

**7. CSV compartido en `apps/core/exportar.py`.** `respuesta_csv(nombre, encabezados, filas)` con BOM, «;» y
`celda_segura` en cada celda, movida desde `apps/gastos/views.py`, que la sigue exportando. Lo usan el CSV del
reporte (mismo archivo que hoy) y el de la cartera (`cartera-AAAA-MM.csv`: condominio, período, emitido,
recaudado, % con coma decimal, deuda anterior, unidades morosas y la fila de totales).

**8. Menú y entrada.** `apps/core/context_processors.py` agrega `tiene_cartera`. En `base.html`, «Cartera» sale
de «Administración» y queda como enlace propio con `{% if tiene_cartera %}`. `core:sin_condominio` redirige a
la cartera a quien tiene acceso, así el administrador general sin membresía llega a ella al iniciar sesión.
Se borra la plantilla provisional.

**9. Pantalla.** Tabla en `.table-responsive`, montos con `|pesos`, % con un decimal y situación con
`.insignia-moroso` («Con morosas») o `.insignia-al-dia` («Sin morosas»). Sin `FiltrosGetMixin` ni chips: el
único filtro es el mes.

**10. Filtro de residencia (#46): no aplica.** La cartera no muestra datos de residentes ni cobros de una
persona: cuenta unidades y montos por condominio, como el reporte, que tampoco usa `cobros_visibles`.

**11. Demo.** `apps/gastos/demo.py` emite un período en Los Aromos. `apps/cartera/demo.py` crea con
`get_or_create` un administrador general ficticio (`gerencia@condohub.cl`, clave `CLAVE_DEMO` de
`apps.cuentas.demo`, RUT ficticio válido) y le asigna los dos condominios, con su evento de auditoría
(`usuario=None`). `--reiniciar` borra las asignaciones en cascada con los condominios.

## Risks / Trade-offs

- [`generar_reporte` lee todos los cobros anteriores de cada condominio] → basta para decenas de condominios;
  si crece, se optimiza en `reportes.py` y la cartera lo hereda.
- [Un borrado en cascada (usuario o condominio) quita asignaciones sin auditarlas] → son borrados excepcionales
  del superusuario; se documenta en el admin.
- [Hasta que se una C4, las cifras incluyen pagos anulados] → igual que el reporte; la prueba de cuadre sigue
  valiendo.
- [El administrador y el comité pierden la página provisional (403)] → es lo que pide el Issue; se actualizan
  las pruebas de C0.
- [La spec `plataforma` pide tablas como tarjetas en el celular, decisión aún abierta] → se usa la misma tabla
  del reporte; se mide a 375 px que la página no se desplace en horizontal.

## Migration Plan

`cartera/0001` crea una tabla vacía. Para revertir: `migrate cartera zero` y revertir el PR.
