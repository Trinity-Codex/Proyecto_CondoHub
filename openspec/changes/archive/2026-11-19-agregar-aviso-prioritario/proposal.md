# Proposal

## Why

El cliente (reunión del 16-nov, requerimiento RQ-03) pidió que los comunicados urgentes ocupen toda la pantalla del residente y no puedan cerrarse sin confirmar la lectura, y saber quién los leyó y cuándo.

Issue: Closes #118. Prioridad MoSCoW: **Should**, hito PMV 27-nov.

## What Changes

- Campo **`prioritario`** en `Comunicado`, que marca el administrador al publicar; exige «Visible hasta» para que el aviso no bloquee para siempre.
- **Pantalla de aviso a pantalla completa**: mientras el residente tenga un aviso prioritario vigente sin confirmar, cualquier página (también una URL escrita a mano) lo lleva a esa pantalla. Se muestran de a uno, por orden de publicación. Solo «He leído este aviso» o «Cerrar sesión».
- La confirmación reutiliza `LecturaComunicado` (fecha y hora). Al confirmar el último, el residente vuelve a la página que había pedido.
- **Lectura por residente** (administrador y comité): quién confirmó, con fecha y hora, y quién falta.
- Insignia «Prioritario» en la lista y el detalle.
- Demo del cliente: un aviso prioritario ficticio para la Torre B; en la demo de solo lectura se permite confirmarlo.

Fuera del alcance:
- Repetir el aviso o pedir autorización para publicarlo (consulta C5 al cliente).
- Correo, contador de no leídos y recordatorios (RQ-04, #120).

## Capabilities

### New Capabilities
- Ninguna.

### Modified Capabilities
- `comunicacion`: modifica «Confirmación de lectura» (lectura por residente para administrador y comité) y agrega «Aviso prioritario».

## Impact

- `apps/comunicados`: campo y migración 0003, consultas, middleware nuevo `middleware.py`, tres vistas, dos plantillas, formulario, demo y pruebas.
- Delegado por Walther: una línea en `MIDDLEWARE` de `config/settings.py`.
- De Winderson (coordinado en el Issue): `comunicados:confirmar_aviso` en `POST_PERMITIDOS` de `apps/core/middleware_demo.py`.
- De Walther: la huella de la demo del cliente en `apps/core/tests_demo_cliente.py` (+1 comunicado, +2 avisos).
- Sin dependencias nuevas.
