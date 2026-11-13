## 1. Código

- [x] 1.1 Filtrar los destinatarios de `Pago.registrar` con `cobros_visibles` en `apps/pagos/models.py`, dejando el aviso solo a los residentes activos que ven el cobro.

## 2. Pruebas

- [x] 2.1 Agregar prueba: no avisa a quien llegó después del período (`apps/pagos/tests.py`, `RegistrarPagosTest`).
- [x] 2.2 Agregar prueba: no avisa a quien ya fue dado de baja (`apps/pagos/tests.py`, `RegistrarPagosTest`).
- [ ] 2.3 Correr `python manage.py test apps` completo con MySQL 8. Pendiente: no hay servidor MySQL en esta máquina; la prueba local se hizo con SQLite.

## 3. Datos demo

- [ ] 3.1 Cambiar la huella de la notificación en `apps/core/tests.py` (`HUELLA["notificaciones"]`) de 22 a 21 (main sumó dos avisos con #58 y #54). Pendiente del OK de Walther: el demo ahora produce un aviso menos, por el residente recién llegado de `apps/condominios/demo.py`.

## 4. Cierre

- [ ] 4.1 Archivar este cambio en el mismo Pull Request, antes de unirlo a main.
