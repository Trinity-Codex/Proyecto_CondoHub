# Design

## Context

#58 dejó la vigencia y la lectura por persona (`LecturaComunicado`). Hace falta un bloqueo que no se pueda saltar escribiendo otra URL y que nunca deje al residente fuera del sitio por un error.

## Goals / Non-Goals

**Goals:** bloquear al residente hasta confirmar cada aviso prioritario vigente; registrar fecha y hora; mostrar al administrador y al comité quién leyó.

**Non-Goals:** modales de JavaScript, notificaciones push, repetición del aviso.

## Decisions

- **Middleware con redirección, no modal.** `AvisoPrioritarioMiddleware.process_view` redirige a `comunicados:aviso_prioritario` cualquier vista que no esté en la lista libre: el aviso, su confirmación, cerrar sesión, cambiar de condominio, las imágenes del encabezado y el admin de Django. Los estáticos no pasan por vistas. Se descartó un modal porque se cierra con las herramientas del navegador y no cubre una URL directa.
- **Pantalla como capa fija opaca** sobre `base.html`, con `role="alertdialog"`, `aria-modal` y el foco en el título. No hay botón de cerrar ni cierre con Escape o clic fuera.
- **Quién se bloquea.** Solo quien es residente y no tiene otro rol en el condominio activo. Un miembro del comité que además vive ahí navega normal (lo dice el Issue: administrador, comité y conserje no se bloquean).
- **Falla abierta.** Si la consulta lanza una excepción, se registra y la petición sigue.
- **Volver a donde iba.** En un GET bloqueado se guarda la ruta pedida en la sesión; al no quedar avisos se redirige a ella solo si es del mismo sitio (`url_has_allowed_host_and_scheme`).
- **Lectura por persona** (`lecturas_por_residente`): una fila por residente activo destinatario, con sus unidades y la fecha de lectura. La vista es para administrador y comité; el conteo por unidad de #58 no cambia.
- **Demo de solo lectura.** `comunicados:confirmar_aviso` se permite: solo guarda la lectura del propio residente, y sin ella la cuenta quedaría bloqueada.

## Risks / Trade-offs

- [Una consulta extra por petición del residente] → un `EXISTS` indexado por condominio; solo para el rol residente.
- [Un aviso mal publicado bloquea a todos] → exige «Visible hasta», y el administrador puede editarlo o quitarle la marca.
