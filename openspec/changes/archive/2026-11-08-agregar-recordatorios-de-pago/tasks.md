# Tasks

## 1. Recordatorios

- [x] 1.1 Crear `RecordatorioEnviado` con su migración (`notificaciones.0002`) y la restricción única (D2). Verificar con una prueba en `apps/notificaciones/tests.py`: no se puede repetir cobro, persona y tipo.
- [x] 1.2 Crear `apps/notificaciones/recordatorios.py` con `Recordatorio` (Sujeto) y `enviar_recordatorios(hoy)` (D1, D3, D4), y suscribirlo en `apps.py`. Verificar con pruebas con fechas simuladas: avisa 3 días antes y el día siguiente; no avisa el día del vencimiento ni fuera de las ventanas; no repite; no avisa a quien pagó, a quien llegó después o fue dado de baja; con pago parcial avisa el saldo; respeta "recibir correos".
- [x] 1.3 Crear el comando `enviar_recordatorios` con `--fecha` (D5). Verificar con una prueba con `call_command` que imprime los avisos enviados y rechaza una fecha inválida.

## 2. Indicadores de cobranza

- [x] 2.1 Agregar los indicadores del último período emitido a `InicioView` y `core/inicio.html` (D6). Verificar con pruebas en `apps/core/tests.py`: el administrador y el comité ven los mismos números que `generar_reporte`; sin períodos emitidos se indica; el conserje y el residente no los ven. Revisar el inicio en el navegador a 360 px.

## 3. Demo

- [x] 3.1 Documentar en `apps/notificaciones/demo.py` cómo ver los recordatorios en la demo con `enviar_recordatorios --fecha`, sin crear datos (ver Risks). Verificar en el navegador corriendo el comando sobre la demo.

## 4. Verificación de integración

- [x] 4.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [x] 4.2 Ejecutar `/code-review high` y corregir lo que corresponda; verificar repitiendo 4.1.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #57`.
- Archivar con `/opsx:archive` antes de unir.
- Actualizar la rama con `main`, repetir 4.1, esperar la CI en verde y unir con la autorización de Maximiliano, a más tardar el sábado 21.
