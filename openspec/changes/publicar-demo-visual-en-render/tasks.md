# Tasks

## 1. Configuración y navegación

- [x] 1.1 Configurar Render en módulo separado con SQLite aislada, secreto y dominio validados, HTTPS, cookies seguras, estáticos WhiteNoise y correo dummy.
- [x] 1.2 Implementar bloqueo de escrituras y revisar GET con efectos, preservando CSRF, autenticación y pertenencia al condominio.
- [x] 1.3 Mostrar aviso y tratar los controles de escritura de forma accesible en el entorno de demo.
- [x] 1.4 Probar operaciones permitidas y bloqueadas, GET sin escritura, pertenencia, secreto y hosts, y comportamiento normal.

## 2. Docker, Runbook y pruebas locales

- [x] 2.1 Crear imagen Python 3.12, exclusiones, arranque idempotente con el comando existente y servicio Render Free con health check de login.
- [x] 2.2 Documentar configuración, arranque, cuentas de referencia, recorrido por rol, reconstrucción, actualización y apagado.
- [x] 2.3 Construir la imagen, comprobar el arranque desde una base vacía y verificar estáticos, aislamiento, preparación repetida y `check --deploy`.
- [x] 2.4 Ejecutar la suite local, revisar migraciones y validar OpenSpec.

## 3. Entrega

- [ ] 3.1 Abrir PR `Refs #111` para revisión de Walther con evidencia, verificación del CI MySQL y pendientes del operador.
- [ ] 3.2 Publicar la versión revisada con el operador, comprobar HTTPS y el recorrido por rol a 1440 y 375 px, estáticos, bloqueo de escrituras, acceso ajeno, reinicio y suspensión. Entregar a Walther URL, commit y evidencias.
