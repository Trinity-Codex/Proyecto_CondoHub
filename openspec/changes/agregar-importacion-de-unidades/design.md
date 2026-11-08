# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver la spec `condominios` de este cambio.

Estado actual que condiciona el diseño:

- `Edificio` es único por condominio y nombre; `Unidad`, por edificio y número. `Residente` es único por usuario y unidad, y su `save()` da el rol RESIDENTE en el condominio.
- `ResidenteForm.save()` ya resuelve la reasignación: reactiva el registro con la nueva fecha `desde` (#46).
- `apps/cuentas` ya tiene `validar_rut_disponible` (un RUT, una cuenta) y `enviar_invitacion` (correo para definir la contraseña, #11).
- `Condominio.suma_alicuotas()` y el aviso de alícuotas descuadradas ya existen.
- No se puede agregar librerías sin necesidad (`requirements.txt` es de Walther): se usa el módulo `csv` de Python.

## Goals / Non-Goals

**Goals:**

- Que el administrador vea todos los errores de una vez, por fila, antes de guardar.
- Todo o nada, y reimportar sin duplicar.
- Que el CSV que guarda Excel en Chile (separado por `;`, a veces en Windows-1252) funcione sin ajustes.

**Non-Goals:**

- Archivos `.xlsx`, dar de baja a quien no está en el archivo o editar cuentas existentes.

## Decisions

### D1. Formato del archivo

Columnas (encabezados en minúscula, sin tildes): `edificio`, `numero`, `piso`, `tipo`, `alicuota`, `correo`, `nombre`, `apellido`, `rut`, `tipo_residente`, `desde`.

- Obligatorias siempre: `edificio`, `numero` y `alicuota`. `piso` vacío es 1 y `tipo` vacío es Departamento.
- Si `correo` está vacío, la fila es solo la unidad. Si tiene correo, `desde` es obligatoria y `tipo_residente` vacío es Propietario. `nombre`, `apellido` y `rut` se exigen solo si el correo no tiene cuenta.
- Una unidad con varios residentes va en varias filas con los mismos datos de unidad.
- Separador `;` o `,`, detectado en la línea de encabezados. Codificación UTF-8 (con o sin BOM) y, si falla, Windows-1252.
- Alícuota como fracción con punto o coma (`0,0125`). Fecha `AAAA-MM-DD`, `DD-MM-AAAA` o `DD/MM/AAAA`. Tipos por su nombre (`Departamento`, `Arrendatario`...) sin importar mayúsculas ni tildes.
- Máximo 1 MB.

### D2. Dos pasos: vista previa y confirmación

1. **Subir:** se lee y valida todo el archivo y se muestra la vista previa. No se guarda nada en la base de datos; el texto del archivo queda en la sesión, junto con el condominio.
2. **Confirmar:** se vuelve a validar el texto de la sesión (los datos pudieron cambiar entre medio) y, si sigue sin errores, se aplica dentro de `transaction.atomic()`. Si algo falla, no queda nada guardado.

El código vive en `apps/condominios/importacion.py`, separado de las vistas: `leer(texto)` → filas; `validar(filas, condominio)` → resultado con errores y resumen; `aplicar(resultado, condominio)` → cuentas nuevas.

### D3. Reimportar sin duplicar

- Edificio: se busca por nombre (sin importar mayúsculas) en el condominio; si no existe, se crea.
- Unidad: se busca por edificio y número; si existe, se actualizan piso, tipo y alícuota.
- Cuenta: se busca por correo. Si existe, no se modifican sus datos. Si no, se crea sin contraseña usable.
- Residente: la misma lógica de `ResidenteForm.save()`: se crea o se reactiva y se actualizan tipo y `desde`.

Para no hacer una consulta por fila, la validación carga antes los edificios, unidades y cuentas involucrados.

### D4. Validaciones

Por fila: campos obligatorios, largo máximo, número de piso, tipo válido, alícuota entre 0 y 1, correo válido, RUT válido y no usado por otra cuenta (ni por otro correo nuevo del archivo), fecha válida y no futura.

Entre filas:

- **Unidad repetida:** la misma unidad con piso, tipo o alícuota distintos.
- **Residente repetido:** el mismo correo dos veces en la misma unidad.
- **Correo repetido con otros datos:** el mismo correo con nombre, apellido o RUT distintos.

Global: la suma de las alícuotas del condominio después de importar (las unidades que no están en el archivo conservan la suya) debe ser 1. Si no, es un error que impide confirmar, con la suma calculada.

### D5. Invitaciones

Al confirmar, la casilla «Enviar invitaciones a las cuentas nuevas» llama a `enviar_invitacion(request, usuario, RESIDENTE)` para cada cuenta creada, con `transaction.on_commit`: si la importación se revierte, no sale ningún correo. Las cuentas que ya existían no reciben invitación.

### D6. Plantilla

`plantilla.csv` se genera desde las mismas columnas de D1, separada por `;` y con BOM UTF-8 para que Excel muestre bien las tildes, con tres filas de ejemplo (unidad con propietario, la misma unidad con un familiar y una unidad sin residente). Una prueba importa la plantilla.

### D7. Acceso

Las vistas usan `RolRequeridoMixin` con `roles_permitidos = [ADMINISTRADOR]` y trabajan siempre sobre `request.condominio`. El botón «Importar planilla» va en la página Unidades, solo para el administrador.

### D8. Auditoría

Crear cuentas y dar roles es un dato personal y un cambio de roles. Cuando C1 (#27) esté en `main`, la importación registra un evento con el resumen. Si no llega a tiempo, va en el PR de eventos de auditoría.

## Risks / Trade-offs

- **El archivo en la sesión:** hasta 1 MB en la sesión de la base de datos. Un condominio de 200 unidades ocupa unos 20 KB.
- **Datos demo:** no hace falta agregar datos; la plantilla sirve como ejemplo para probar en la demo.
- **Alícuotas exactas:** la suma debe dar exactamente 1, como ya exige el aviso de la página Unidades.
