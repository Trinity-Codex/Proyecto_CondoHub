# Tasks

## 1. Aviso de privacidad

- [ ] 1.1 Reemplazar la página provisional por el aviso completo (D5), con secciones y advertencia de datos de demostración. Verificar con pruebas en `apps/privacidad/tests.py`: se lee sin sesión, contiene cada sección y la advertencia, y todos los roles lo ven; revisarlo en el navegador a 360 px.
- [ ] 1.2 Agregar el enlace al aviso en `iniciar_sesion.html` (`apps/cuentas`). Verificar con una prueba que el inicio de sesión lo enlaza, además del pie.

## 2. Solicitudes del titular

- [ ] 2.1 Crear `SolicitudTitular` con su migración (`privacidad.0001`) y los métodos `presentar()` y `cerrar()` como Sujeto (D1, D3). Verificar con pruebas del modelo: estado inicial, cierre con respuesta y fecha, y que no se cierra dos veces.
- [ ] 2.2 Suscribir `SolicitudTitular` a la campana y al correo en `apps/notificaciones/apps.py`. Verificar con pruebas: al presentar, avisa a los administradores activos del condominio; al cerrar, avisa a la persona.
- [ ] 2.3 Crear las vistas, formularios y plantillas de la persona: presentar y "Mis solicitudes" (D2), enlazadas desde el aviso y Mi perfil. Verificar con pruebas: presentar en el condominio activo, ver solo las propias, 404 al abrir una ajena.
- [ ] 2.4 Crear las vistas del administrador: lista del condominio y "Responder y cerrar", con el acceso desde la página Usuarios. Verificar con pruebas: comité, conserje y residente reciben 403; una solicitud de otro condominio da 404; la respuesta es obligatoria.

## 3. Descarga de mis datos

- [ ] 3.1 Crear `DescargarMisDatosView` (D4) y el botón en Mi perfil. Verificar con pruebas: responde JSON como archivo descargable, no incluye la contraseña, incluye cuenta, roles, residencias, reservas, incidentes, solicitudes y notificaciones, y sin sesión redirige al inicio de sesión.
- [ ] 3.2 Probar que los cobros del archivo respetan el período de residencia (#46): un cobro anterior a la llegada no aparece y uno posterior sí.

## 4. Datos demo y auditoría

- [ ] 4.1 Agregar en `apps/privacidad/demo.py` una solicitud pendiente de `residente@condohub.cl` y otra cerrada de `residente2@condohub.cl`. Verificar con `cargar_demo --reiniciar` en el navegador: el administrador ve las dos y cada residente solo la suya.
- [ ] 4.2 Cuando C1 (#27) esté en `main`, registrar en la auditoría la presentación y el cierre de una solicitud (D6). Verificar con una prueba que cada acción deja su evento. Si C1 no llega antes del domingo 15, mover esta tarea al PR de eventos de auditoría y dejarlo anotado.

## 5. Verificación de integración

- [ ] 5.1 Correr `python manage.py makemigrations --check`, `python manage.py test apps` con MySQL y `openspec validate --all --strict`; todo debe pasar.
- [ ] 5.2 Ejecutar `/code-review high` con `opus` (nivel A del plan: datos personales) y corregir lo que corresponda; verificar repitiendo 5.1.

## Workflow follow-up

- Publicar la propuesta en un PR borrador con `Closes #51`.
- Archivar con `/opsx:archive` antes de unir.
- Actualizar la rama con `main`, repetir 5.1, esperar la CI en verde y unir con la autorización de Maximiliano, a más tardar el domingo 15.
