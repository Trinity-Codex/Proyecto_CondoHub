# Prueba guiada de usabilidad y accesibilidad (#59)

**Issue:** #59 · **Equipo:** Walther Mora, Maximiliano Soto y Winderson Castrillo · **Fechas:** miércoles 25 y jueves 26 de noviembre de 2026, después del congelamiento.

Material para que 3 a 5 personas usen CondoHub desde su celular, con datos ficticios, mientras medimos cuánto se demoran, dónde se equivocan y cuánta ayuda necesitan. Junto con la revisión de accesibilidad, da la evidencia propia que pide la defensa (RNF03, RNF10 y NTI-12 del Informe 1).

| Archivo | Para qué |
|---|---|
| [consentimiento.md](consentimiento.md) | Se lee al participante y se marca su aceptación antes de empezar |
| [guion.md](guion.md) | Lo que dice y hace quien modera, y las tareas por rol |
| [registro.csv](registro.csv) | Una fila por participante y tarea (se abre con Excel) |
| [informe.md](informe.md) | Informe breve con los resultados. La revisión de accesibilidad ya está completa |

## Roles del equipo en cada sesión

| Rol | Qué hace |
|---|---|
| Moderador | Lee el guion, entrega las tareas y no ayuda salvo que la persona lo pida o lleve 2 minutos sin avanzar |
| Observador | Toma el tiempo y anota en `registro.csv` errores, ayudas y comentarios |
| Soporte | Prepara el celular y la cuenta demo, y vuelve los datos a su estado inicial entre participantes |

Con dos personas, el observador también hace de soporte.

## Antes de la primera sesión

1. Demo publicada (o servidor local en la misma red Wi-Fi) con `cargar_demo --reiniciar`, para que todos partan con los mismos datos.
2. Cuentas: `residente@condohub.cl` para las tareas del residente y `administrador@condohub.cl` para las de reserva. La clave de la demo está en el README del proyecto. **No se usan datos reales de nadie.**
3. Celular con la sesión cerrada, el navegador en la página de inicio de sesión y el brillo alto. Si la persona prefiere el suyo, se usa el suyo.
4. Cronómetro (el del celular del observador) y `registro.csv` abierto.
5. Probar las cuatro tareas una vez de punta a punta. Si algo falla, se anota y se avisa en el grupo antes de empezar.

## Cómo llenar `registro.csv`

Separado por `;` (el CSV de Excel en Chile). Una fila por participante y tarea; copiar las filas de P1 para cada persona.

| Columna | Valor |
|---|---|
| `resultado` | `solo` (lo logró sin ayuda), `con ayuda` o `no logró` |
| `tiempo_seg` | Segundos desde que toca la pantalla hasta que cumple el criterio de éxito |
| `errores` | Cantidad: páginas que no la acercan a la tarea o formularios enviados con errores |
| `ayudas` | Cantidad de pistas que dio el moderador |
| `facilidad_1_7` | Respuesta a «¿Qué tan fácil fue?» (1 = muy difícil, 7 = muy fácil) |
| `comentarios` | Frases textuales de la persona y lo que observó el equipo |

## Entre participantes

- Cerrar sesión y borrar lo que creó el participante (la reserva y el incidente), o recargar la demo con `cargar_demo --reiniciar`.
- Guardar el registro con el código del participante (P1, P2…), nunca con su nombre.

## Después de las sesiones

1. Completar [informe.md](informe.md) con los números de `registro.csv`.
2. Cada problema **grave** (la persona no logró la tarea, o hubo que ayudarla) se corrige antes de la entrega del viernes 27 o queda como Issue con la etiqueta `prioridad: alta`.
3. Publicar el informe en un PR que diga `Closes #59`.
