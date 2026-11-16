# Tasks

## 1. Configuración y navegación

- [ ] 1.1 Configurar Render en módulo separado con SQLite aislada, secreto y dominio validados, HTTPS, cookies seguras, estáticos WhiteNoise y correo dummy.
- [ ] 1.2 Implementar bloqueo de escrituras y revisar GET con efectos, preservando CSRF, autenticación y pertenencia al condominio.
- [ ] 1.3 Mostrar aviso y tratar los controles de escritura de forma accesible en el entorno de demo.
- [ ] 1.4 Probar operaciones permitidas y bloqueadas, GET sin escritura, pertenencia, secreto y hosts, y comportamiento normal.

## 2. Docker, Runbook y pruebas locales

- [ ] 2.1 Crear imagen Python 3.12, exclusiones, arranque idempotente con el comando existente y servicio Render Free con health check de login.
- [ ] 2.2 Documentar configuración, arranque, cuentas de referencia, recorrido por rol, reconstrucción, actualización y apagado.
- [ ] 2.3 Construir la imagen, comprobar el arranque desde una base vacía y verificar estáticos, aislamiento, preparación repetida y `check --deploy`.
- [ ] 2.4 Ejecutar la suite habitual, revisar migraciones y validar OpenSpec. Confirmar CI MySQL.

## 3. Entrega

- [ ] 3.1 Abrir PR `Refs #111` para revisión de Walther con evidencia y pendientes del operador.
- [ ] 3.2 Publicar la versión revisada con el operador, comprobar HTTPS y el recorrido por rol a 1440 y 375 px, estáticos, bloqueo de escrituras, acceso ajeno, reinicio y suspensión. Entregar a Walther URL, commit y evidencias.
