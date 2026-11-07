# Tasks

## 1. Modelo y migración

- [x] 1.1 Agregar `desde`, `hasta` y la restricción `hasta >= desde` a `Residente`, y hacer que `save()` mantenga `hasta` coherente con `activo` (D4, D5). Verificar con pruebas en `apps/condominios/tests.py`: baja guarda la fecha de hoy, reactivar la limpia y `dar_de_baja()` persiste ambos campos.
- [x] 1.2 Crear una sola migración con la carga de datos conservadora (D6). Verificar con una prueba de la función de migración: el menor entre membresía y cobro más antiguo, sin datos usa la fecha de la migración, inactivos quedan con `hasta` nulo. Comprobar además `migrate condominios 0001` y volver a `migrate` en la base local.

## 2. Contrato C2

- [x] 2.1 Crear `apps/condominios/residencias.py` con `cobros_visibles(cobros, usuario)` y su documentación de uso para #6, #56 y #57 (D1, D2, D3). Verificar con pruebas: llegada a mitad de mes, período anterior y posterior, cambio de año, `hasta` definido, residente inactivo, otra unidad, varios residentes sin cobros duplicados, y que el resultado se puede seguir encadenando.
- [x] 2.2 Aplicar `cobros_visibles` en `cobros_del_residente()` de `apps/pagos/consultas.py` (excepción acordada) y fechar en 2020 las residencias de `crear_escenario()` en `apps/core/pruebas.py` (excepción que requiere el visto bueno de Walther en el PR borrador). Verificar que las pruebas existentes de `pagos` y `gastos` pasan sin editarlas.
- [x] 2.3 Probar el comportamiento completo en `apps/condominios/tests.py`: Mi cuenta oculta cobros anteriores, el detalle responde 404, "Mi deuda" no los suma, cobranza y reporte muestran la deuda completa, y un comité que también es residente ve filtrada su cuenta y completa la cobranza.

## 3. Pantallas del administrador

- [x] 3.1 Agregar `desde` a `ResidenteForm` con calendario, hoy como valor inicial y rechazo de fechas futuras; al reasignar, guardar la nueva fecha. Verificar con pruebas: fecha faltante, futura, pasada y reasignación; y que comité, conserje y residente reciben 403.
- [x] 3.2 Mostrar la fecha de inicio de cada residente en `unidades.html` y agregar `desde` y `hasta` a `ResidenteAdmin`. Verificar con una prueba que la fecha aparece en la página Unidades y revisándola en el navegador a 360 px.

## 4. Datos demo

- [ ] 4.1 Cuando #62 esté en `main`, fijar las fechas en `apps/condominios/demo.py`: residentes con fecha antigua y `residente2` (B-102) desde el mes anterior, para que no vea el cobro de hace dos meses. Verificar con `cargar_demo --reiniciar` en el navegador: Mi cuenta de `residente@condohub.cl` muestra todos sus cobros, la de `residente2@condohub.cl` no muestra el más antiguo, y la cobranza sí.

## 5. Verificación de integración

- [ ] 5.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [ ] 5.2 Ejecutar `/code-review high` con `opus` (nivel A del plan) y corregir lo que corresponda; verificar repitiendo 5.1.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #46` y avisar en el grupo a Walther (`apps/core/pruebas.py`) y a Winderson (`apps/pagos/consultas.py`), antes de implementar.
- Archivar con `/opsx:archive` (`sonnet` · `low`) antes de unir.
- Actualizar la rama con `main`, repetir 5.1, marcar el PR como listo y esperar la CI en verde. Maximiliano hace el **Squash and merge** y avisa en el grupo la firma de `cobros_visibles`, a más tardar el miércoles 11.
