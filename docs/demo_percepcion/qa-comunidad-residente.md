# QA de comunidad y recorrido del residente — demo del 16-nov

**Issue:** #99 · **Responsable:** Maximiliano Soto · **Fecha:** lunes 16-nov-2026

Verificación del bloque de comunidad para la primera reunión con el cliente. No cambia código: es
evidencia y el recorrido sugerido. Los datos son ficticios.

## 1. Estado verificado

| Elemento | Valor |
|---|---|
| Base de código | `main` en `e4bb7d3` + PR #108 (#95, tarifas con `pesos`) + PR de #96 (actividad ficticia) |
| Base de datos | Demo aislada SQLite (`.demo_cliente/demo.sqlite3`), creada con `preparar_demo_cliente --settings=config.settings_demo` |
| Fecha de referencia | `DEMO_FECHA_REFERENCIA = 2026-11-16` |
| Servidor | `runserver 127.0.0.1:8018 --settings=config.settings_demo`, cerrado al terminar |
| Base habitual | No se tocó: ninguna escritura fuera de la base de demo |
| Navegador | Chromium (Playwright). Anchos 375×812 y 1440×900; se mide `document.documentElement.scrollWidth <= innerWidth` |

> **Nota del entorno de verificación:** sin acceso al CDN, Bootstrap 5.3 se sirvió desde una copia
> local (sin SRI) solo para medir. Sin Bootstrap las tablas no tienen `overflow-x: auto` y se ven
> desbordes que no existen en la demo real.

## 2. Matriz de rutas

Esperado/observado = código HTTP sin seguir redirecciones. Anchos: 375 · 1440 (solo páginas 200).
Los ID corresponden a la demo aislada: comunicado 5 = «Retiro de bicicletas abandonadas en Torre A»,
2 = corte de agua de la Torre B (vencido), 3 = comunicado de Los Aromos; espacio 1 = Quincho,
4 = Sala multiuso de Los Aromos.

| Rol | Ruta | Qué se comprueba | Esperado | Observado | Anchos |
|---|---|---|---|---|---|
| anónimo | `/cuentas/iniciar-sesion/` | Inicio de sesión | 200 | 200 | ok · ok |
| anónimo | `/privacidad/` | Aviso de privacidad público | 200 | 200 | ok · ok |
| anónimo | `/` | Inicio redirige al login | 302 | 302 | — |
| anónimo | `/comunicados/` | Comunicados exige sesión | 302 | 302 | — |
| administrador | `/` | Panel del administrador | 200 | 200 | ok · ok |
| administrador | `/condominio/unidades/` | Unidades y residentes | 200 | 200 | ok · ok |
| administrador | `/condominio/unidades/importar/` | Importar CSV | 200 | 200 | ok · ok |
| administrador | `/cuentas/usuarios/` | Usuarios | 200 | 200 | ok · ok |
| administrador | `/cuentas/usuarios/nuevo/` | Alta de usuario | 200 | 200 | ok · ok |
| administrador | `/comunicados/` | Comunicados vigentes | 200 | 200 | ok · ok |
| administrador | `/comunicados/?vigencia=vencidos` | Comunicados vencidos | 200 | 200 | ok · ok |
| administrador | `/comunicados/5/` | Detalle con conteo de lectura | 200 | 200 | ok · ok |
| administrador | `/comunicados/nuevo/` | Nuevo comunicado | 200 | 200 | ok · ok |
| administrador | `/reservas/` | Espacios con tarifas | 200 | 200 | ok · ok |
| administrador | `/reservas/espacios/1/` | Detalle de espacio | 200 | 200 | ok · ok |
| administrador | `/reservas/todas/` | Todas las reservas | 200 | 200 | ok · ok |
| administrador | `/reservas/espacios/nuevo/` | Nuevo espacio | 200 | 200 | ok · ok |
| administrador | `/privacidad/solicitudes/` | Solicitudes del titular | 200 | 200 | ok · ok |
| administrador | `/cuentas/perfil/` | Perfil | 200 | 200 | ok · ok |
| administrador | `/reservas/nueva/` | Solo residentes reservan | 403 | 403 | — |
| residente | `/` | Panel del residente | 200 | 200 | ok · ok |
| residente | `/comunicados/` | General y dirigido a Torre A | 200 | 200 | ok · ok |
| residente | `/comunicados/5/` | Dirigido a su torre, leído | 200 | 200 | ok · ok |
| residente | `/comunicados/2/` | Comunicado de la Torre B: no visible | 404 | 404 | — |
| residente | `/comunicados/3/` | Comunicado de otro condominio | 404 | 404 | — |
| residente | `/reservas/` | Espacios | 200 | 200 | ok · ok |
| residente | `/reservas/espacios/1/` | Disponibilidad del Quincho | 200 | 200 | ok · ok |
| residente | `/reservas/mis-reservas/` | Mis reservas | 200 | 200 | ok · ok |
| residente | `/reservas/nueva/` | Nueva reserva | 200 | 200 | ok · ok |
| residente | `/reservas/espacios/4/` | Espacio de otro condominio | 404 | 404 | — |
| residente | `/reservas/todas/` | Todas las reservas: solo administración | 403 | 403 | — |
| residente | `/condominio/unidades/` | Unidades: solo administración | 403 | 403 | — |
| residente | `/cuentas/usuarios/` | Usuarios: solo administración | 403 | 403 | — |
| residente | `/privacidad/mis-solicitudes/` | Mis solicitudes | 200 | 200 | ok · ok |
| residente | `/privacidad/mis-solicitudes/nueva/` | Nueva solicitud | 200 | 200 | ok · ok |
| residente | `/cuentas/perfil/` | Perfil | 200 | 200 | ok · ok |
| residente2 | `/comunicados/` | Sin el vencido en la lista | 200 | 200 | ok · ok |
| residente2 | `/comunicados/?vigencia=vencidos` | Corte de agua en vencidos | 200 | 200 | ok · ok |
| residente2 | `/reservas/mis-reservas/` | Su reserva del Salón | 200 | 200 | ok · ok |
| gerencia | `/cartera/` | Cartera de los dos condominios | 200 | 200 | ok · ok |
| gerencia | `/comunicados/` | Sin rol en condominios: va a /sin-condominio/ | 302 | 302 | — |
| gerencia | `/condominio/unidades/` | Sin rol en condominios | 302 | 302 | — |

**Resultado: 42 de 42 rutas con el código esperado, sin pantallas 500 ni desbordes a 375 o 1440 px.**
Los 403 y 404 son esperados (permisos y aislamiento entre condominios), no errores de la demo.

## 3. Comprobaciones de contenido

| Comprobación | Resultado |
|---|---|
| Tarifas con puntos de miles: «$15.000 por reserva» y «Sin costo» en el gimnasio (#95) | OK |
| El residente de A-101 ve el comunicado general vigente y el dirigido a la Torre A (#96) | OK |
| El comunicado vencido de la Torre B no aparece en la lista principal de residente2 | OK |
| …y sí aparece en «Ver vencidos» | OK |
| El administrador ve el conteo de lectura por unidad en el comunicado dirigido | OK |
| «Todas las reservas» muestra las reservas próximas del Gimnasio y del Salón (#96) | OK |
| El residente ve solo su propia reserva (Quincho), no la del Salón de B-102 | OK |
| La cuenta de gerencia ve la cartera de los dos condominios y no tiene rol dentro de ellos | OK |
| Inicio de sesión: todos los campos tienen etiqueta asociada | OK |

## 4. Recorrido sugerido: comunidad y residente (3 a 4 minutos)

Clave de todas las cuentas: `condohub2026`.

1. **Administrador** (`administrador@condohub.cl`) → *Unidades y residentes*: dos torres, alícuotas y
   residentes por unidad. Mencionar la importación desde CSV sin entrar al flujo.
2. → *Comunicados*: abrir «Retiro de bicicletas abandonadas en Torre A» y mostrar el conteo de
   lectura por unidad. Volver y abrir «Ver vencidos» para mostrar que lo vencido no estorba.
3. → *Espacios comunes*: tarifas en pesos y «Todas las reservas» con las próximas de la semana.
4. **Cerrar sesión e ingresar como residente** (`residente@condohub.cl`, A-101) → *Inicio*: su
   panel. → *Comunicados*: solo lo general y lo de su torre, con el suyo marcado como leído.
5. → *Espacios comunes* → Quincho: disponibilidad del día y «Mis reservas».
6. Cierre: *Privacidad* (pie de página), el aviso y la solicitud de derechos del titular.

Alternativa si falta tiempo: pasos 2, 4 y 5.

## 5. Límites conocidos (decirlos sin simular)

- Auditoría y rendición mensual siguen como páginas provisionales; el aviso de cobro en PDF y el
  comprobante de pago son próximos pasos del PMV.
- La demo es local y con datos ficticios; la versión publicada en internet es parte del PMV (#29).
- La cuenta de gerencia no tiene rol dentro de los condominios: desde *Comunicados* o *Unidades*
  vuelve a la página de sin condominio. Usarla solo para la cartera.
- Las reservas y comunicados de #96 se cuentan desde la fecha de la demo o desde el día en que se
  prepara la base, la que sea posterior: si se recrea la base después del lunes, siguen siendo próximos.

## 6. Hallazgos

Ningún bloqueo para el ensayo en el bloque de comunidad. Lo único que apareció (tablas que se
desbordaban a 375 px) fue efecto del entorno sin Bootstrap y desaparece con la hoja de estilos real.
