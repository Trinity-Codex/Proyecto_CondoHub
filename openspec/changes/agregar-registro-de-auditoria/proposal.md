Issue: #27 (`Refs #27` en este PR, `Closes #27` en el de la vista). MoSCoW: Must.
Fuera de alcance: la vista, los eventos de pagos e incidentes y la protección a nivel de base de datos.

## Why

CondoHub maneja dinero, roles y datos personales de residentes, pero hoy no guarda quién cambió qué ni cuándo.
El comité y la administración necesitan esa trazabilidad para responder ante una discrepancia, y el Informe 1
la exige como requisito Must (RNF11, SEG-05, NTI-09). Entrega PMV: 27 de noviembre de 2026.

## What Changes

- Nuevo modelo `RegistroAuditoria` con usuario, condominio, acción, objeto (tipo e id), valores anteriores y
  nuevos en JSON, y fecha. Se guarda en la app `auditoria`.
- Servicio `apps.auditoria.servicios.registrar(usuario, condominio, accion, objeto, antes=None, despues=None)`
  como único punto de entrada para registrar eventos (contrato C1 del plan del PMV).
- Los registros son inmutables: no se pueden editar ni borrar desde el código ni desde el admin de Django.
- Vista de auditoría filtrable (por fecha, usuario, acción y objeto) para el administrador y el comité.
  Conserje y residente reciben 403. Llega en un segundo PR.
- Eventos mínimos: emisión de un período, registro y anulación de pagos (#53), alta de usuarios, cambios de
  rol o membresía, cambio de alícuota y cambio de estado de un incidente. Cada uno tiene su prueba.
- Este cambio (PR núcleo, `Refs #27`) cubre el modelo, el servicio, la inmutabilidad y sus pruebas. Los eventos
  de pagos e incidentes, y la vista, van en el PR de vista.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: se agrega el requisito «Registro de auditoría» (ADDED). El Issue #27 indica esta spec como
  principal, porque la auditoría es transversal a todas las apps y no pertenece a una sola.

## Impact

- **Código:** `apps/auditoria/` (modelo, migración `0001`, `servicios.py`, pruebas en `tests.py`). Se reemplaza la
  página provisional de `AuditoriaInicioView` cuando llegue la vista, en el PR siguiente.
- **Migraciones:** solo en `apps/auditoria`, una por PR. Nunca se edita una migración ya unida a `main`.
- **Dependencias externas:** ninguna.
- **Otros integrantes:** Walther usa `registrar()` en #8 (miércoles 18) y Maximiliano en los eventos de cuentas
  y condominios (viernes 13). Su firma no cambia sin aviso en el grupo.
- **Datos demo:** se agregan en `apps/auditoria/demo.py` para que la vista se vea en la demo del PMV.
