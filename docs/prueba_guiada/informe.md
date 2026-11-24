# Informe de la prueba guiada de usabilidad y accesibilidad (#59)

**Issue:** #59 · **Equipo:** Walther Mora, Maximiliano Soto y Winderson Castrillo · **Sesiones:** 25 y 26 de noviembre de 2026
**Estado:** la revisión de accesibilidad (sección 2) está completa; las secciones 1, 3 y 4 se llenan después de las sesiones.

Requisitos que respalda: RNF03 (usabilidad), RNF10 (accesibilidad) y NTI-12 (Informe 1). Meta de accesibilidad: WCAG 2.1 AA en los flujos del residente.

## 1. Participantes

| Código | Vive en condominio | Comodidad con el celular (1-5) | Celular propio | Ayudas técnicas |
|---|---|---|---|---|
| P1 | | | | |
| P2 | | | | |
| P3 | | | | |

Datos ficticios en todas las tareas. Sin nombres ni datos personales de los participantes (ver [consentimiento](consentimiento.md)).

## 2. Revisión de accesibilidad (sábado 21 de noviembre)

**Método.** Revisión automática propia, ejecutada en el navegador sobre la demo local a 375 × 812 px (celular),
con la sesión de `residente@condohub.cl`. Por cada página se comprobó:
- contraste de cada texto visible (4,5:1; 3:1 en texto grande), calculado sobre el fondo real;
- etiqueta de cada campo, nombre accesible de botones y enlaces, texto alternativo de imágenes;
- idioma, título, un solo `h1`, región `<main>` e ids sin repetir;
- texto ampliado al 200 % sin desplazamiento horizontal (WCAG 1.4.4);
- formularios enviados con errores: `aria-invalid` y mensaje enlazado con `aria-describedby`.

No se usó axe ni Lighthouse: cargar librerías externas en el entorno de revisión no estaba permitido. Se recomienda confirmar con Lighthouse (pestaña de DevTools de Chrome) en la demo publicada.

**Páginas revisadas (15).** Inicio de sesión, inicio, Mi cuenta, detalle de un cobro, Mi aporte al fondo, Espacios comunes, Nueva reserva, Mis reservas, Incidentes, Reportar incidente, detalle de un incidente, Comunicados, detalle de un comunicado, Notificaciones, Mi perfil y Aviso de privacidad. Además, los formularios de reserva e incidente enviados vacíos.

**Resultados.**

| Criterio WCAG 2.1 | Resultado |
|---|---|
| 1.1.1 Contenido no textual | ✅ Todas las imágenes con `alt` |
| 1.3.1 Información y relaciones | ✅ Campos con etiqueta; errores enlazados al campo |
| 1.4.3 Contraste mínimo | ✅ Todo el texto cumple. La «b» naranja del logo (2,65:1) está exenta por ser parte de un logotipo |
| 1.4.4 Cambio de tamaño del texto | ⚠️ → ✅ Seis páginas con desplazamiento horizontal al 200 %; todas corregidas (PR #144 y #147) |
| 2.4.2 Título de página | ✅ Todas con título |
| 3.1.1 Idioma de la página | ✅ `lang="es"` |
| 3.3.1 Identificación de errores | ✅ `aria-invalid` y mensaje por campo |
| 4.1.2 Nombre, función, valor | ✅ Botones y enlaces con nombre accesible |

**Hallazgos de 1.4.4 (texto al 200 % a 375 px).**

| Página | Qué se salía | Estado |
|---|---|---|
| Inicio | «Reportar incidente» (+14 px) | Corregido (#144) |
| Espacios comunes | «Reservar» (+45 px) | Corregido (#144) |
| Nueva reserva | «Cancelar» (+59 px) | Corregido (#144) |
| Notificaciones | «Marcar todas como leídas» (+85 px) | Corregido (#144) |
| Reportar incidente | «Cancelar» (+23 px) | Corregido (#147, Winderson) |
| Detalle de un cobro | Montos con `text-nowrap` (+98 px) | Corregido (#147, Winderson) |

Verificación después de las correcciones (lunes 23 de noviembre): las seis páginas miden 375 px de ancho con el texto al 200 %, sin desplazamiento horizontal.

**Mejora sugerida (no exigida por AA).** Al enviar un formulario con errores, mover el foco al primer campo con error o a un resumen, para quien navega con teclado o lector de pantalla.

## 3. Resultados por tarea

Completar con `registro.csv`. Tasa de éxito = participantes que la lograron solos ÷ total.

| Tarea | Éxito sin ayuda | Con ayuda | No lograron | Tiempo mediano (s) | Errores (promedio) | Facilidad (1-7, mediana) |
|---|---|---|---|---|---|---|
| T1. Ver la deuda | | | | | | |
| T2. Descargar el aviso | | | | | | |
| T3. Reservar el quincho | | | | | | |
| T4. Reportar un incidente | | | | | | |

**Accesibilidad en vivo.** ¿Agrandaron el texto? ¿Se pudo leer todo sin desplazar de lado? Comentarios de quien usa ayudas técnicas.

## 4. Problemas encontrados y decisión

Gravedad: **grave** (no logró la tarea o necesitó ayuda), **moderado** (lo logró con errores o lento), **menor** (comentario o detalle visual).

| # | Tarea | Problema | Participantes | Gravedad | Decisión (corregido en PR / Issue) |
|---|---|---|---|---|---|
| 1 | | | | | |

## 5. Conclusión

Resumen en 3 o 4 líneas: qué tan bien resolvieron las tareas, qué se corrigió antes de la entrega y qué queda como Issue.
