# Guion de la prueba guiada (#59)

Unos 15 a 20 minutos por persona. Quien modera lee el texto entre comillas tal cual, para que todos los
participantes reciban las mismas instrucciones.

## 1. Bienvenida (2 min)

1. Leer el [consentimiento](consentimiento.md) y marcar las casillas.
2. «Te voy a pedir unas tareas. Mientras las haces, piensa en voz alta: cuéntame qué buscas y qué esperas que pase. No hay respuestas buenas ni malas.»
3. «Yo no te voy a ayudar a menos que me lo pidas, porque queremos ver si el sitio se entiende solo.»

## 2. Preguntas iniciales (1 min)

Se anotan en `registro.csv` (columnas de perfil, en la fila de la tarea T0):

- «¿Vives en un condominio o edificio?» (sí / no)
- «¿Cómo te enteras hoy de tus gastos comunes?» (papel, correo, otro sitio, no sé)
- «Del 1 al 5, ¿qué tan cómodo te sientes usando el celular para trámites?»

## 3. Tareas del residente (10 a 12 min)

Ingreso: el soporte deja abierta la página de inicio de sesión. La primera tarea incluye entrar.

Para cada tarea:
- El moderador la lee y el observador **inicia el tiempo** cuando la persona toca la pantalla.
- **Se detiene el tiempo** cuando se cumple el criterio de éxito o la persona dice que terminó.
- **Ayuda:** si la persona la pide, o lleva 2 minutos sin avanzar, el moderador da la pista de la tabla y el observador la anota.
- **Error:** cada vez que entra a una página que no la acerca a la tarea, o envía un formulario con errores.
- Al terminar: «Del 1 al 7, ¿qué tan fácil fue? (1 = muy difícil, 7 = muy fácil)» (columna `facilidad_1_7`).

| Tarea | Lo que lee el moderador | Éxito cuando… | Pista si la pide |
|---|---|---|---|
| **T1. Ver la deuda** | «Entra con el correo `residente@condohub.cl` y la clave que te doy. Averigua cuánto debes en total de gastos comunes.» | Dice el monto total que debe (está en el inicio, tarjeta de deuda, o en «Mi cuenta») | «Mira el inicio o el menú, en Mi cuenta» |
| **T2. Descargar el aviso** | «Descarga el aviso de cobro del último mes para guardarlo o imprimirlo.» | Se abre o descarga el PDF del aviso de cobro | «Entra a Mi cuenta y abre el cobro del mes» |
| **T3. Reservar el quincho** | «Reserva el quincho para el próximo sábado, de 13:00 a 16:00.» | La reserva queda creada y la persona ve la confirmación | «En el menú, Reservas» |
| **T4. Reportar un incidente** | «En tu pasillo hay una ampolleta quemada. Avísale a la administración.» | Aparece el mensaje «Incidente #N reportado. Te avisaremos cuando cambie su estado.» | «En el menú, Incidentes» |

Si el quincho no está disponible ese sábado, se ofrece el domingo a la misma hora y se anota en comentarios.

### Tareas de reserva (si sobra tiempo o el participante es administrador de verdad)

| Tarea | Lo que lee el moderador | Éxito cuando… |
|---|---|---|
| **T5. Leer un comunicado** (residente) | «Revisa si la administración publicó algo y marca que lo leíste.» | Pulsa «Marcar como leído» en un comunicado |
| **T6. Publicar un comunicado** (con `administrador@condohub.cl`) | «Avisa a todo el condominio que el lunes se limpian los estanques.» | El comunicado queda publicado |
| **T7. Ver quién debe** (administrador) | «Averigua cuántas unidades están morosas este mes.» | Dice el número (está en el inicio y en Cobranza) |

## 4. Accesibilidad en vivo (2 min)

Con la persona, en su mismo celular:
1. «¿Puedes agrandar el texto como lo harías normalmente?» (zoom con dos dedos o tamaño de letra del sistema). Observar si se lee todo sin desplazar de lado.
2. Si usa lector de pantalla o letra grande, anotar en comentarios qué funcionó y qué no.

## 5. Cierre (2 min)

- «¿Qué fue lo más fácil? ¿Y lo más difícil?»
- «Si pudieras cambiar una sola cosa, ¿cuál sería?»
- «¿Usarías algo así en tu condominio?» (sí / no / tal vez)
- Agradecer. Recordar que puede pedir que borremos lo anotado.

## Qué no hacer

- No decir dónde está un botón antes de que la persona lo pida.
- No corregir ni apurar. Si la persona se frustra, se ofrece pasar a la siguiente tarea.
- No usar datos reales del participante ni anotarlos en ningún lugar.
