# Estudio de factibilidad: comunicados redactados y enviados con apoyo de IA

**Issue:** #124 (RQ-10) · **Responsable:** Maximiliano Soto · **Fecha:** 19-nov-2026 · **MoSCoW:** Won't (fuera de esta entrega)

> Estudio para decidir con el cliente. **No se escribió código ni se crearon cuentas o claves con proveedores.**
> Cliente y datos simulados.

## 1. Pregunta

El cliente preguntó si los comunicados del administrador podrían redactarse y enviarse automáticamente con
inteligencia artificial. Antes de desarrollar hay que saber qué alcance tiene, cuánto cuesta y qué datos de
residentes saldrían de CondoHub.

Contexto actual: el administrador redacta el comunicado; CondoHub lo publica, avisa por la campana y por
correo (patrón Observer) y mide la lectura (#58, #118, #120).

## 2. Alternativas

| | A. Borrador con IA y aprobación del administrador | B. Envío totalmente automático | C. Sin IA: plantillas |
|---|---|---|---|
| Cómo funciona | El administrador escribe la idea («corte de agua jueves 10 a 14 h, Torre B»), la IA propone título y texto, él edita y pulsa «Publicar». | La IA redacta y publica sola a partir de un evento o una instrucción, sin revisión. | Textos tipo editables (corte de agua, mantención, asamblea, simulacro) con campos a completar. |
| Ventajas | Ahorra tiempo de redacción y mejora el tono, y la persona responsable sigue decidiendo. El flujo de publicación no cambia. | Máximo ahorro de tiempo. | Sin costo variable, sin proveedor externo y sin datos fuera de CondoHub. Predecible. |
| Riesgos | Dependencia de un proveedor externo; el administrador puede aprobar sin leer. | Errores de fecha, hora o destinatario publicados sin control; tono inadecuado; difícil asignar responsabilidad ante la comunidad. | Menos flexible: no ayuda con casos fuera de las plantillas. |
| Tamaño estimado | M (1 Issue, 3 a 5 días) | L, y no se recomienda | S (1 a 2 días) |

## 3. Costo mensual estimado

**Supuestos (explícitos):** un condominio tipo publica **20 comunicados al mes** (más que el uso real esperado,
para no subestimar). Cada comunicado usa **3 llamadas** a la IA (borrador y dos ajustes). Cada llamada tiene unos
**800 tokens de entrada** (instrucciones, ejemplo de estilo y nota del administrador) y **400 de salida** (título
y texto). Total por condominio: 48.000 tokens de entrada y 24.000 de salida al mes.

Precios por uso, tarifa estándar, en dólares por millón de tokens (entrada / salida), **consultados el 19-11-2026**:

| Modelo (proveedor) | Precio entrada / salida | Costo por condominio al mes | 50 condominios | Fuente |
|---|---|---|---|---|
| gpt-5-nano (OpenAI) | US$ 0,05 / 0,40 | US$ 0,012 | US$ 0,60 | [OpenAI, precios de la API](https://developers.openai.com/api/docs/pricing.md) |
| Claude Haiku 5.5 (Anthropic) | US$ 0,10 / 0,50 (prompts de hasta 100.000 tokens) | US$ 0,017 | US$ 0,84 | [Claude, precios](https://platform.claude.com/en/docs/about-claude/pricing) |
| gpt-4o-mini (OpenAI) | US$ 0,15 / 0,60 | US$ 0,022 | US$ 1,08 | [OpenAI, precios de la API](https://developers.openai.com/api/docs/pricing.md) |
| Gemini 3.5 Flash-Lite (Google, nivel pagado) | US$ 0,30 / 2,50 | US$ 0,074 | US$ 3,72 | [Gemini API, precios](https://ai.google.dev/gemini-api/docs/pricing) |
| Claude Sonnet 5.5 (Anthropic, mayor calidad) | US$ 2 / 10 | US$ 0,34 | US$ 16,80 | [Claude, precios](https://platform.claude.com/en/docs/about-claude/pricing) |

Lectura: con un modelo pequeño, el costo de la IA es de **centavos de dólar al mes por condominio**; aun con
diez veces más uso, no llega a US$ 0,25. Lo que sí cuesta es el desarrollo (alternativa A, tamaño M) y la
operación (claves, monitoreo de errores y del gasto).

Fuera de este cálculo:
- El **correo** ya lo envía CondoHub al publicar, con o sin IA. Su costo depende del servicio SMTP que se elija
  en #29, no de la IA.
- Impuestos, tipo de cambio y planes empresariales.
- Los precios cambian seguido. Por ejemplo, Google informa que Gemini 3.8 Flash duplica su precio desde el
  01-01-2027. Hay que revisarlos antes de implementar.

## 4. Privacidad

**Qué datos viajarían al proveedor en cada alternativa:**

| Alternativa | Datos que salen de CondoHub |
|---|---|
| A. Borrador con aprobación | Solo la nota del administrador y variables **no personales**: nombre del condominio, edificio, fecha, hora y tipo de aviso. **Nunca** nombres, RUT, correos, teléfonos, unidades ni deudas de residentes. La lista de destinatarios la arma CondoHub después, como hoy. |
| B. Automático | Igual que A si se diseña bien. El riesgo es que, para «decidir solo», se le entreguen datos de residentes (morosidad, incidentes con nombre), lo que no se recomienda. |
| C. Plantillas | Ninguno. |

**Lo que declaran los proveedores** (consultado el 19-11-2026):
- **Anthropic (API):** por defecto no retiene los prompts ni las respuestas, salvo en algunos modelos que exigen
  retención de 30 días. Los datos retenidos no se usan para entrenar sin permiso expreso. Retención cero (ZDR)
  disponible bajo solicitud
  ([API y retención de datos](https://platform.claude.com/docs/en/build-with-claude/api-and-data-retention)).
- **OpenAI (API):** desde el 01-03-2023 los datos de la API no se usan para entrenar, salvo que el cliente lo
  active. Guarda registros de abuso hasta 30 días; retención cero solo para clientes aprobados
  ([Tus datos en la API](https://developers.openai.com/api/docs/guides/your-data)).
- **Google (Gemini API):** el nivel gratuito puede usarse para mejorar sus productos; el **pagado no**. Solo
  debe usarse el nivel pagado ([Gemini API, precios](https://ai.google.dev/gemini-api/docs/pricing)).
- Los tres procesan fuera de Chile, así que es una **transferencia internacional** de datos.

**Normativa chilena.** El documento del cliente cita la Ley 19.628. La **Ley 21.719**, que la reforma, entra en
vigencia el **01-12-2026**
([IAPP](https://iapp.org/news/a/d-a-de-la-pdp-en-chile-estamos-preparados-para-la-entrada-en-vigor-de-la-normativa)).
Un proyecto que la posterga al 15-10-2027 fue aprobado por el Senado el 28-10-2026 y sigue en la Cámara: mientras
no se publique, rige la fecha original
([Diario Constitucional, 09-11-2026](https://www.diarioconstitucional.cl/opinion/la-ley-que-espera-a-su-guardian-la-postergacion-de-la-ley-n-21719-y-lo-que-el-proyecto-deja-sin)).
Con la alternativa A sin datos personales, el riesgo es bajo. Si algún día se envían datos personales, el
proveedor sería un encargado de tratamiento y la transferencia internacional necesitaría base legal y
cláusulas contractuales (hay cláusulas tipo aprobadas en diciembre de 2025, según la misma fuente de IAPP).
Esto debe validarlo quien asesore legalmente al cliente: este estudio no es una opinión legal.

## 5. Riesgos de calidad y cómo los cubre la alternativa A

| Riesgo | Ejemplo | Mitigación en A |
|---|---|---|
| Datos inventados o cambiados | La IA escribe «jueves 15» cuando era «jueves 14». | El administrador revisa antes de publicar. Fecha y hora van como campos del formulario y se insertan tal cual, sin que la IA las reescriba. |
| Tono inadecuado | Demasiado informal o alarmista. | Instrucción fija de tono formal y cercano, y un ejemplo de estilo del condominio. |
| Destinatario equivocado | Un aviso de la Torre B enviado a todos. | Los destinatarios los elige el administrador en el formulario actual («Dirigido a»), no la IA. |
| Proveedor caído o lento | Error o espera al pedir el borrador. | Falla abierta: se escribe a mano, como hoy. La IA nunca bloquea publicar. |
| Aprobación sin leer | Se pulsa «Publicar» sin revisar. | Vista previa obligatoria, marca «Redactado con ayuda de IA» visible solo para el administrador, y auditoría (#27). |

## 6. Recomendación

1. **Para esta entrega: alternativa C** (plantillas). Es barata, no tiene proveedor externo ni riesgo de datos,
   y resuelve los casos más comunes. Puede tomarse como Issue S apenas el cliente lo pida.
2. **Siguiente entrega, si el cliente lo confirma: alternativa A** con un modelo pequeño (Claude Haiku 5.5 o
   gpt-5-nano), sin datos personales y con aprobación obligatoria. El costo es despreciable; lo que hay que
   presupuestar es el desarrollo.
3. **No recomendada: alternativa B.** Publicar sin revisión traslada al software una responsabilidad que hoy
   recae en el administrador.

**Issue de implementación sugerido (si el cliente aprueba A):** «Borrador de comunicado con IA, con aprobación
del administrador». Tamaño **M**. Alcance: botón «Sugerir redacción» en el formulario, servicio aislado
(`apps/comunicados/redaccion_ia.py`) que solo recibe la nota y las variables no personales, clave por variable
de entorno, límite de llamadas por condominio, falla abierta, auditoría del uso y pruebas con un proveedor falso.

## 7. Pasos externos para Walther (solo si el cliente aprueba A)

- [ ] Elegir el proveedor con el cliente y crear la cuenta de la organización (no personal), en el nivel pagado.
- [ ] Generar la clave de API y guardarla como variable de entorno en el despliegue (#29), nunca en el repositorio.
- [ ] Fijar un **límite de gasto mensual** en el panel del proveedor.
- [ ] Revisar y aceptar los términos comerciales y, si aplica, pedir retención cero.
- [ ] Registrar al proveedor como encargado en la documentación de privacidad (#51).

## 8. Pregunta al cliente (consulta C10)

> «Para los comunicados con apoyo de IA, ¿prefieren que la IA **proponga un borrador que el administrador revisa
> y aprueba** antes de enviarlo (recomendado), o que **se envíen automáticamente** sin revisión? Mientras deciden,
> ¿les sirve contar con **plantillas** de comunicados frecuentes (cortes de agua, mantenciones, asambleas,
> simulacros)? ¿Cuáles serían las más útiles?»
