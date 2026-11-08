# Proposal

Closes #13 · MoSCoW: **Should** · Hito PMV 27-nov (se corta primero si hay atraso) · RF01.

## Why

Hoy cada edificio, unidad y residente se crea a mano desde la página Unidades. Cargar un condominio de 200 unidades así es inviable, y los sistemas del mercado (ComunidadFeliz, EdiPro, Kastor) ofrecen la migración con una planilla.

## What Changes

- **Importar desde planilla:** el administrador sube un CSV (el que guarda Excel) con edificio, número, piso, tipo, alícuota y, si la unidad tiene residente, su correo, nombre, apellido, RUT, tipo de residente y fecha `desde` (#46).
- **Vista previa antes de confirmar:** cuántas filas son válidas y, por fila, qué está mal (RUT inválido o de otra cuenta, correo repetido con otros datos, unidad repetida, alícuota o fecha inválida). También avisa si las alícuotas del condominio, después de importar, no suman 1.
- **Todo o nada:** si hay cualquier error, no se importa nada; al confirmar, todo se guarda en una transacción.
- **Reimportar no duplica:** edificios, unidades y residentes se buscan por nombre, número y correo; si ya existen se actualizan.
- **Cuentas nuevas e invitaciones:** si el correo no tiene cuenta, se crea; al confirmar, el administrador elige si enviar las invitaciones para que definan su contraseña (#11).
- **Plantilla CSV de ejemplo** descargable desde la misma página.

**Fuera del alcance:**
- Archivos `.xlsx`: se pide guardar la planilla como CSV, así no se agrega una librería a `requirements.txt`.
- Dar de baja a quien no aparece en el archivo: importar solo agrega y actualiza.
- Modificar los datos de una cuenta que ya existía (nombre, RUT).
- Importar otros roles (comité, conserje): siguen en Usuarios.
- El registro en auditoría queda para cuando C1 (#27) esté en `main`; si no llega a tiempo, va en el PR de eventos de auditoría (`Refs #27`).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `condominios`: se agrega el requisito «Importación desde planilla».

## Impact

- **Mis carpetas:** `apps/condominios` (módulo de importación, vistas, plantillas, rutas y pruebas). Reutiliza `enviar_invitacion` y `validar_rut_disponible` de `apps/cuentas` sin cambiarlas.
- **Sin cambios** en `config/`, `templates/base.html`, `requirements.txt` ni en el modelo de datos (no hay migraciones).
- **Dependencias:** usa la fecha `desde` de C2 (#46, ya en `main`); C1 (#27) para la auditoría.
