# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver la spec `privacidad` de este cambio.

Estado actual que condiciona el diseño:

- #62 dejó la app `privacidad` registrada, con `AvisoPrivacidadView` pública (sin `RolRequeridoMixin`), la ruta `privacidad:aviso`, el enlace en el pie y un `demo.py` vacío que `cargar_demo` ya llama.
- El menú (`templates/base.html`) es de Walther: el administrador entra a las solicitudes desde la página Usuarios (`apps/cuentas`), que es suya.
- `cobros_visibles(cobros, usuario)` (#46) decide qué cobros ve una persona.
- El Observer (`apps/notificaciones/apps.py`) suscribe los sujetos a la campana y al correo.

## Goals / Non-Goals

**Goals:**

- Un aviso legible en el celular, con secciones claras.
- Un ciclo de solicitud simple: pendiente → cerrada con respuesta.
- Una descarga que reúna lo de la persona sin exponer datos de otros.

**Non-Goals:**

- Estados intermedios (en revisión, rechazada) y adjuntos en las solicitudes.
- Ejecutar automáticamente la supresión u oposición.

## Decisions

### D1. Modelo `SolicitudTitular`

Campos:

- `usuario` y `condominio` (FK).
- `tipo`: ACCESO, RECTIFICACION, SUPRESION u OPOSICION.
- `detalle`.
- `estado`: PENDIENTE o CERRADA.
- `respuesta`.
- `creada`, `cerrada` y `cerrada_por` (FK nula).

La solicitud pertenece al condominio activo, porque el responsable del tratamiento es la administración de cada condominio.

- **Alternativa descartada:** una solicitud global a la plataforma. Nadie en el condominio la vería, y la plataforma es encargada, no responsable.

### D2. Vistas

- **`MisSolicitudesView` y `SolicitudCreateView`:** cualquier miembro, con `RolRequeridoMixin`; filtran por `usuario=request.user` y el condominio activo.
- **`SolicitudesView` y `ResponderSolicitudView`:** solo el administrador, con `RolRequeridoMixin` y `CondominioQuerysetMixin`. Una solicitud de otro condominio da 404.
- **Responder:** un formulario con la respuesta obligatoria, que cierra la solicitud en un solo paso.

### D3. Avisos con el Observer

`SolicitudTitular` hereda de `Sujeto`:

- `presentar()` avisa a los administradores activos del condominio.
- `cerrar(respuesta, por)` avisa a la persona.

Se suscribe a la campana y al correo en `apps/notificaciones/apps.py`, como los demás sujetos.

### D4. Descarga en JSON

`DescargarMisDatosView` (con `LoginRequiredMixin`, como Mi perfil) arma un diccionario y lo entrega con `JsonResponse` y `Content-Disposition: attachment`.

- **Incluye:** la cuenta (sin contraseña), las membresías, las residencias con sus fechas, las reservas que hizo, los incidentes que reportó, sus solicitudes, sus notificaciones y los cobros con sus pagos, filtrados con `cobros_visibles(..., incluir_bajas=True)`: una residencia dada de baja sigue contando dentro de sus fechas, porque esos cobros siguen siendo datos de la persona. La respuesta va sin caché (`no-store`).
- **Fechas:** en ISO 8601; los montos, como enteros.
- **Formato:** JSON porque es estructurado y de lectura automática. CSV obligaría a separar cada sección en un archivo distinto.
- **Dónde vive:** la vista va en `apps/privacidad`, y Mi perfil solo enlaza.

### D5. El texto del aviso

Va en una plantilla, porque no es editable por el administrador en el PMV. Tiene secciones fijas:

- responsable y encargado;
- datos y finalidades;
- conservación;
- derechos y cómo ejercerlos;
- reclamos ante la autoridad.

Incluye una advertencia visible de datos de demostración. Menciona los registros técnicos de #52 (correo e IP de intentos fallidos, por poco tiempo).

Los plazos se expresan sin cifras legales que el equipo no ha validado.

### D6. Auditoría

Presentar y cerrar una solicitud llaman a `apps.auditoria.servicios.registrar` (C1) cuando esté en `main`. Si C1 no llega a tiempo, esa llamada va en el PR de eventos de auditoría (`Refs #27`), y la tarea queda marcada como pendiente.

## Risks / Trade-offs

- [El texto puede no cumplir todo lo que exige la Ley 21.719] → se declara como borrador de demostración y se sugiere revisión legal antes de un uso real.
- [La descarga puede ser lenta para alguien con muchas notificaciones] → aceptado para el PMV; los volúmenes son chicos.
- [Una persona sin condominio activo no puede presentar solicitudes] → aceptado: el aviso indica el correo de contacto de la administración como alternativa.
- [Hasta que se una C1, las solicitudes no quedan en la auditoría] → tarea separada y explícita.

## Migration Plan

Agrega una tabla nueva (`privacidad.0001`). Para revertir: `python manage.py migrate privacidad zero`.
