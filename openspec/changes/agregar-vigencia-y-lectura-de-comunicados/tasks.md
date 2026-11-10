# Tasks

## 1. Vigencia

- [ ] 1.1 Agregar `vigente_hasta` a `Comunicado`, `vigentes()` y `vencidos()` al QuerySet, y la migración `comunicados.0002` (D1). Verificar con pruebas en `apps/comunicados/tests.py`: el día indicado todavía es vigente y el siguiente no; sin fecha siempre es vigente.
- [ ] 1.2 Agregar «Visible hasta» al formulario con `CampoFecha`, rechazando una fecha pasada salvo la que ya tenía (D1). Verificar con pruebas al publicar y al editar.
- [ ] 1.3 Lista principal y panel de inicio solo con vigentes, enlace «Ver vencidos (N)» con `?vigencia=vencidos` e insignia «Vencido» en la lista y el detalle (D2). Verificar con pruebas: el vencido no está en la lista ni en el inicio, sí en vencidos y su detalle responde 200.

## 2. Confirmación de lectura

- [ ] 2.1 Crear `LecturaComunicado` con la restricción única en la misma migración `0002`, y `Comunicado.confirmaciones()` (D3, D4). Verificar con pruebas: dos residentes de la misma unidad cuentan una vez; solo cuentan las unidades destinatarias con residentes activos; un comunicado por edificio cuenta solo las de ese edificio.
- [ ] 2.2 Crear `MarcarLeidoView` y el botón en el detalle (D5). Verificar con pruebas: marca una sola vez; un residente de otro edificio recibe 404; comité y conserje 403; el detalle muestra «Leíste este comunicado».
- [ ] 2.3 Mostrar «X de Y unidades confirmaron» en la lista y el detalle, y las unidades que faltan en el detalle, solo al administrador. Verificar con pruebas y en el navegador a 360 px.

## 3. Demo

- [ ] 3.1 Actualizar `apps/comunicados/demo.py` (D6) sin agregar comunicados. Verificar con `CargarDemoTest` y en el navegador.

## 4. Verificación de integración

- [ ] 4.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [ ] 4.2 Ejecutar `/code-review high` y corregir lo que corresponda; verificar repitiendo 4.1.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #58`.
- Archivar con `/opsx:archive` antes de unir.
- Actualizar la rama con `main`, repetir 4.1, esperar la CI en verde y unir con la autorización de Maximiliano.
