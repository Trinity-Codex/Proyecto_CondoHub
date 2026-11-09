# Tasks

Pruebas en `apps/cartera/tests.py` salvo que se indique otra cosa. Escenarios con datos ficticios de
`crear_escenario()` y un segundo condominio creado en la prueba.

## 1. Acceso de administrador general (modelo, admin y auditoría)

- [x] 1.1 Crear `AsignacionCartera` (usuario, condominio, `asignada_el`, única por par) y la migración `cartera/0001`; verificar con `python manage.py makemigrations --check` y una prueba de que el par repetido se rechaza.
- [x] 1.2 Crear `apps/cartera/permisos.py` con `condominios_de_cartera(usuario)` y `CarteraRequeridaMixin`; probar que devuelve solo los asignados y activos, todos para el superusuario y ninguno para quien no tiene asignaciones.
- [x] 1.3 Registrar `AsignacionCarteraAdmin` solo para el superusuario, con alta y baja sin edición; probar escenario «Acceso por rol» de `condominios` (staff sin superusuario, administrador, comité, conserje, residente y administrador general no entran a la página del admin).
- [x] 1.4 Registrar con `registrar()` y `Accion.CAMBIAR_ROL` el alta (`save_model`) y la baja (`delete_model` y `delete_queryset`) en una transacción; probar «Asignar…» y «Quitar el acceso…» (un registro por condominio, con el id de la persona y sin su nombre ni RUT en `antes`/`despues`) y el borrado en lote.

## 2. Descarga CSV compartida

- [x] 2.1 Crear `apps/core/exportar.py` con `celda_segura` y `respuesta_csv`, y hacer que `ReporteCsvView` la use (`apps/gastos/views.py` sigue exportando `celda_segura`); verificar que `apps/gastos/tests_reportes.py` pasa sin cambios y probar `respuesta_csv` (BOM, «;», neutralización) en `apps/core/tests.py`.

## 3. Reporte con un condominio dado

- [x] 3.1 Dividir `ReporteMixin` en una base sin permisos (`get_condominio_reporte()`, URL de página y CSV por atributo) y la versión con `RolRequeridoMixin`; parametrizar migas y enlace CSV de `gastos/reporte.html`; verificar que las pruebas actuales del reporte pasan sin cambios y que `reportes.py` no cambia (`git diff --stat`).

## 4. Vista de cartera

- [x] 4.1 Crear `apps/cartera/consolidado.py` (filas por condominio con `generar_reporte` y totales); probar «Cifras iguales al reporte de cada condominio» comparando cada fila con `generar_reporte` y con el contexto de `gastos:reporte` del mismo período, y «Condominio sin período emitido en el mes».
- [x] 4.2 Crear `CarteraView` (`/cartera/`) con el selector de mes (`?mes=AAAA-MM`, `_campo.html`), tabla con `|pesos` e insignias; probar «Mes por defecto y mes inválido» (incluido el caso sin períodos), «Solo los condominios asignados», «Superusuario» y «Acceso por rol» (cuatro roles con 403 y sin sesión al login).
- [x] 4.3 Crear la descarga `cartera:csv` con `respuesta_csv`; probar «Descarga en CSV segura» (condominio «=SUMA(1)», una fila por condominio y la de totales) y que respeta los asignados y el mes.
- [x] 4.4 Crear `/cartera/<pk>/reporte/` y su CSV sobre la base del punto 3; probar «Reporte de un condominio desde la cartera» (mismas cifras que la fila, el condominio activo de la sesión no cambia, 404 para un condominio no asignado en la página y el CSV) y el 403 por rol.
- [x] 4.5 Probar «Sin datos personales»: con una residente ficticia con nombre y RUT en el condominio, ni la cartera, ni el reporte desde ella, ni sus dos CSV contienen ese nombre ni el RUT (con y sin puntos).

## 5. Menú y entrada

- [x] 5.1 Agregar `tiene_cartera` al context processor, el enlace propio «Cartera» en `base.html` y borrar la plantilla provisional; probar que el enlace aparece para el administrador general y el superusuario y no para administrador, comité, conserje ni residente, y actualizar las pruebas de la página provisional de C0.
- [x] 5.2 Redirigir `core:sin_condominio` a la cartera para quien tiene acceso (solo esa función de `apps/core/views.py`); probar «Sin rol dentro del condominio»: el administrador general sin membresía que abre el inicio, las unidades, los gastos comunes o la cobranza termina en la cartera y el selector no le ofrece condominios.

## 6. Datos demo y documentación

- [x] 6.1 Emitir un período en Los Aromos en `apps/gastos/demo.py` y crear en `apps/cartera/demo.py` el administrador general ficticio con los dos condominios demo y su evento de auditoría; verificar que `python manage.py cargar_demo --reiniciar` corre dos veces seguidas sin error y que la cartera demo muestra dos filas con cifras.
- [x] 6.2 Sumar el administrador general a la tabla de usuarios demo de `README.md` y a la salida de `cargar_demo`, y documentar `respuesta_csv` y `condominios_de_cartera` en `docs/GUIA_NUEVA_FEATURE.md`; verificar que los correos y rutas citados existen.

## 7. Verificación integral

- [x] 7.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` completo y `openspec validate --all --strict`, todos sin errores.
- [x] 7.2 Verificación visual con el servidor en el puerto 8054: con el administrador general demo, medir en el DOM a 375 y 1440 px la cartera y el reporte desde ella (`document.documentElement.scrollWidth <= innerWidth`, sin desborde horizontal de la página); guardar capturas en el scratchpad de la sesión y cerrar el servidor.
- [ ] 7.3 Ejecutar `/code-review high` sobre la rama y corregir o justificar cada hallazgo en el PR.

## Workflow follow-up

- Actualizar la rama con `main` (`git fetch origin` y `git merge origin/main`), en especial si ya se unió C4 (#53), y repetir 7.1.
- Archivar con `/opsx:archive` en el mismo PR antes de unir.
- Pasar el PR de borrador a listo; la unión con *Squash and merge* la decide Walther (a más tardar el domingo 15).
