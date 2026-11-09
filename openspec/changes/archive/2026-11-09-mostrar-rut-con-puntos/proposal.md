# Proposal

Issue: #77 (`Closes #77`). MoSCoW: Could. Cambio transversal: lo implementa Walther en `apps/core`, `apps/cuentas` y
`apps/condominios` (Maximiliano) y `apps/proveedores` (Winderson), con aviso al unir. Depende de #75 y #76 (ya en `main`).
Fuera de alcance: aceptar un RUT sin guion («123456785») en el servidor, formatear el RUT en el admin de Django, en el JSON de
«Descargar mis datos» ni en los mensajes de error de la importación CSV, y la ficha de detalle (#82). Los PDF aún no muestran RUT.

## Why

El RUT se escribe de cualquier forma, el error del dígito verificador aparece solo al enviar, y las tablas lo muestran
como se guarda (`12345678-5`), difícil de leer. El Issue pide formato en vivo, aviso accesible y visualización con puntos.

## What Changes

- `formatear_rut` en `apps/core/formato.py`, junto con `normalizar_rut`, `calcular_dv` y `RUT_FORMATO`, que se mueven allí desde
  `apps/cuentas/validadores.py`; este los reexporta, así que nadie que ya los importe cambia.
- Filtro `|rut` (`apps/core/templatetags/condohub.py`) para tablas, fichas y PDF. No se agregan propiedades a los modelos.
- `RutInput` y `RutField` (`apps/core/campos.py`): `data-rut`, placeholder ficticio válido `12.345.678-5`, valor mostrado con puntos y
  valor limpio siempre normalizado (`12345678-5`).
- JS: `rut` en el registro `FORMATOS` de `static/js/formato.js`. Puntos y guion en vivo; aviso «RUT válido.» en una región
  `aria-live="polite"` desde 8 caracteres y el error del dígito verificador solo al salir del campo. Nunca borra ni cambia dígitos sin avisar.
- `_campo.html` y el filtro `control` agregan esa región solo a los campos de RUT, enlazada con `aria-describedby` (extensión compatible de C6).
- Cambian: alta de usuario y Mi perfil (`cuentas`), formulario de proveedor (`proveedores`); listados de usuarios (`cuentas`),
  proveedores y, solo para el administrador, residentes en Unidades (`condominios`). Sin migraciones.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plataforma`: nuevo requisito «RUT legible en formularios y listados», transversal.

## Impact

- Código: `apps/core/formato.py`, `campos.py`, `templatetags/condohub.py`, `templatetags/formularios.py`, `templates/_campo.html`,
  `static/js/formato.js`, `apps/cuentas/validadores.py`, `forms.py`, plantilla `usuarios.html`, `apps/proveedores/forms.py` y `lista.html`,
  `apps/condominios/templates/condominios/unidades.html`; pruebas en `apps/core`, `cuentas`, `proveedores` y `condominios`.
- Sin migraciones ni dependencias. Lo guardado no cambia. Contratos C0 a C6 sin cambios de firma.
