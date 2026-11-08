# Tasks

## 1. Lectura y validación

- [x] 1.1 Crear `apps/condominios/importacion.py` con `leer()` (D1): separador `;` o `,`, UTF-8 con o sin BOM y Windows-1252, encabezados obligatorios. Verificar con pruebas en `apps/condominios/tests.py`: lee ambos separadores y ambas codificaciones, y rechaza un archivo sin los encabezados.
- [x] 1.2 Agregar `validar()` con las validaciones por fila, entre filas y de alícuotas (D4). Verificar con una prueba por cada error: RUT inválido o de otra cuenta, correo repetido con otros datos, unidad repetida, residente repetido, alícuota, piso, tipo y fecha inválidos, fecha futura y alícuotas que no suman 1.

## 2. Importación

- [x] 2.1 Agregar `aplicar()` dentro de `transaction.atomic()` (D3). Verificar con pruebas: crea edificios, unidades, cuentas y residentes con su `desde` y rol RESIDENTE; reimportar el mismo archivo no duplica nada; si falla una fila, no queda nada guardado.
- [x] 2.2 Enviar las invitaciones al confirmar si se marca la casilla (D5). Verificar con pruebas: con la casilla, solo las cuentas nuevas reciben el correo; sin ella, ninguno.

## 3. Pantallas

- [x] 3.1 Crear las vistas de subir, vista previa y confirmar (D2, D7), con el botón «Importar planilla» en Unidades. Verificar con pruebas: la vista previa no guarda nada; con errores no se puede confirmar; confirmar revalida; comité, conserje y residente reciben 403.
- [x] 3.2 Crear la descarga de la plantilla (D6). Verificar con pruebas: es un CSV descargable, solo para el administrador, y la importación la acepta. Revisar la pantalla en el navegador a 360 px.

## 4. Auditoría

- [ ] 4.1 Cuando C1 (#27) esté en `main`, registrar la importación en la auditoría (D8). Verificar con una prueba. Si C1 no llega antes del jueves 19, mover esta tarea al PR de eventos de auditoría y dejarlo anotado.

## 5. Verificación de integración

- [x] 5.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [x] 5.2 Ejecutar `/code-review high` (nivel A del plan: transacción completa y reimportar sin duplicar) y corregir lo que corresponda; verificar repitiendo 5.1.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #13`.
- Archivar con `/opsx:archive` antes de unir.
- Actualizar la rama con `main`, repetir 5.1, esperar la CI en verde y unir con la autorización de Maximiliano, a más tardar el jueves 19.
