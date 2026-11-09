# Mejoras de interfaz para llevar a CondoHub

Reporte del 9-nov-2026. Reúne las mejoras de paneles y formularios del inventario de contratos de Grupo Tattersall que sirven para CondoHub, y cómo adaptarlas.

**Para quién es:** el equipo de CondoHub o un agente que trabaje en ese repositorio.

**Cómo usarlo:**
1. Copiar este archivo a `Proyecto_CondoHub/docs/`.
2. Tomar las secciones en el orden del plan sugerido (§9).
3. Cada sección indica el archivo de origen en el repo de contratos. Úsenlo como referencia y no lo copien a ciegas: los nombres, colores y reglas de negocio son de Tattersall.

## 1. Compatibilidad

| | Contratos (origen) | CondoHub (destino) | Consecuencia |
|---|---|---|---|
| Framework | Django 5.2 LTS | Django 5.2.18 | Formularios, filtros y plantillas se traspasan casi tal cual |
| CSS | Bootstrap 5.3 + `tattersall.css` con variables | Bootstrap 5.3.3 (CDN) + `condohub.css` | Las clases funcionan; los colores salen de las variables de CondoHub |
| Formularios | Componente por campo (`campo.html`) + filtro `control` | Un `_formulario.html` que recorre todos los campos | Conviene sumar el componente por campo (§2) |
| Montos | `DecimalField` con moneda (CLP, UF, USD, EUR) | `PositiveIntegerField` en pesos | Sirve el formato de miles sin decimales (§4) |
| RUT | Validación, formato y visualización con puntos | Validación en `apps/cuentas/forms.py` | Faltan el formato en vivo y la visualización con puntos (§3) |
| JS | Archivos sueltos por pantalla, sin build | Sin JS propio | Mismo enfoque: JS progresivo, sin npm |
| Filtros de listados | `django-filter` | No está en `requirements.txt` | Agregarlo con versión exacta, o filtrar a mano en la vista (§6) |

**Principio general:** cada mejora es progresiva. Sin JavaScript, el formulario funciona igual y el servidor valida, formatea y calcula todo. El JS solo ayuda mientras se escribe.

## 2. Formulario por secciones con ayudas en cada campo

**Problema que resolvió:** los usuarios no sabían a qué se refería cada campo ni qué formato usar.

**Patrón:**
- **Secciones en tarjetas numeradas** (1 Documento, 2 Contraparte, 3 Datos, 4 Plazos y monto). Cada una abre con una frase que explica para qué sirve. El número va en un círculo con `aria-hidden="true"`, porque el `h2` ya da el orden.
- **Cada campo lleva tres capas de ayuda:**
  - una etiqueta clara (`labels`);
  - un ejemplo realista en el `placeholder` («Ej.: Av. Apoquindo 3000, Las Condes»);
  - una ayuda bajo el campo (`help_texts`) que dice **para qué sirve o qué pasa con el dato**, no lo que ya dice la etiqueta.
- **Los opcionales empiezan su ayuda con «Opcional.»** El asterisco rojo marca los obligatorios y la cabecera lo explica: «Los campos con * son obligatorios».
- **Las listas desplegables muestran «Seleccione…»** en vez de `---------` (`rotular_vacios`).
- **Las subsecciones** (p. ej. «Contacto en la contraparte») usan `.subtitulo-seccion`, con una línea superior y sin otra tarjeta.
- **Los bloques condicionales** (`data-bloque="..."`) se muestran u ocultan según una casilla. Sin JS todos quedan visibles.

**Origen:**
- `contratos/templates/contratos/nuevo.html`
- `contratos/formularios.py` (Meta `labels`, `help_texts`, `widgets`; helpers `_texto`, `_numero`, `_selector_fecha`, `rotular_vacios`)
- `interfaz/templates/interfaz/componentes/campo.html`
- `interfaz/templatetags/marca.py` (filtros `control` y `es_casilla`)

**Componente por campo.** Es lo más valioso para CondoHub, porque permite armar grillas de 2 o 3 columnas en vez de un campo bajo otro:

```django
{% load formularios %}{% if campo|es_casilla %}
  <div class="form-check">
    {{ campo|control }}
    <label class="form-check-label" for="{{ campo.id_for_label }}">{{ campo.label }}</label>
    {% if campo.help_text %}<div class="form-text" id="{{ campo.auto_id }}_helptext">{{ campo.help_text }}</div>{% endif %}
    {% for error in campo.errors %}<div class="invalid-feedback d-block" id="{{ campo.auto_id }}_error">{{ error }}</div>{% endfor %}
  </div>
{% else %}
  <div>
    <label class="form-label" for="{{ campo.id_for_label }}">{{ campo.label }}{% if campo.field.required %} <span class="text-danger" aria-hidden="true">*</span>{% endif %}</label>
    {% if prefijo %}<div class="input-group"><span class="input-group-text" data-prefijo>{{ prefijo }}</span>{{ campo|control }}</div>{% else %}{{ campo|control }}{% endif %}
    {% if campo.help_text %}<div class="form-text" id="{{ campo.auto_id }}_helptext">{{ campo.help_text }}</div>{% endif %}
    {% for error in campo.errors %}<div class="invalid-feedback{% if prefijo %} d-block{% endif %}" id="{{ campo.auto_id }}_error">{{ error }}</div>{% endfor %}
  </div>
{% endif %}
```

```python
# templatetags/formularios.py
from django import forms, template

register = template.Library()


def _clase_control(widget):
    if isinstance(widget, forms.CheckboxInput | forms.RadioSelect | forms.CheckboxSelectMultiple):
        return "form-check-input"
    if isinstance(widget, forms.Select):
        return "form-select"
    return "form-control"


@register.filter
def control(campo):
    """Widget con clases de Bootstrap; si hay error, el lector de pantalla lee ayuda y error."""
    widget = campo.field.widget
    clases = [widget.attrs.get("class", ""), _clase_control(widget)]
    atributos = {}
    if campo.errors:
        clases.append("is-invalid")
        atributos["aria-invalid"] = "true"
        descripciones = [f"{campo.auto_id}_error"]
        if campo.help_text:
            descripciones.insert(0, f"{campo.auto_id}_helptext")
        atributos["aria-describedby"] = " ".join(descripciones)
    atributos["class"] = " ".join(c for c in clases if c)
    return campo.as_widget(attrs=atributos)


@register.filter
def es_casilla(campo):
    return isinstance(campo.field.widget, forms.CheckboxInput)
```

**Uso:**

```django
<div class="col-md-6">{% include "_campo.html" with campo=form.rut %}</div>
```

El `_formulario.html` actual puede seguir para formularios cortos. También puede reescribirse para que incluya `_campo.html` en su bucle.

**Botones de opción con fieldset.** Sirven para 2 a 4 opciones con descripción, como «Criticidad» en contratos o el tipo de unidad en CondoHub. Origen: `interfaz/templates/interfaz/componentes/opciones.html`. El grupo va en un `<fieldset>` con `<legend>`. La ayuda admite una línea por opción con `{{ campo.help_text|linebreaksbr }}`, que escapa el texto antes de insertar los `<br>`. En el formulario, el widget es `forms.RadioSelect({"class": "form-check-input"})`.

## 3. RUT: formato en vivo, validación inmediata y visualización con puntos

**Problema que resolvió:** se escribía el RUT de cualquier forma (`123456785`, `12.345.678-5`, `12345678-5`) y el error del dígito verificador solo aparecía al enviar.

**Patrón:**
- **Se guarda normalizado** (`12345678-5`) y **se muestra con puntos** (`12.345.678-5`). El usuario puede escribirlo como quiera.
- **Mientras se escribe**, el JS agrega puntos y guion y deja el cursor tras el mismo dígito.
- **Validación con aviso en vivo:**
  - Con 8 o más caracteres, si el dígito verificador cuadra, aparece en verde «RUT válido.».
  - El error («El dígito verificador no corresponde: revise el RUT.») solo aparece **al salir del campo** (`blur`), para no regañar a medio escribir.
  - El mensaje vive en un `<div aria-live="polite">`, así el lector de pantalla lo anuncia.
- **El ejemplo del placeholder debe ser un RUT válido.** En contratos se usó `76.123.456-0`; uno con el dígito equivocado confunde.

**Origen:**
- `maestros/rut.py` (`normalizar_rut`, `digito_verificador`, `rut_valido`, `formatear_rut`)
- `contratos/static/contratos/formulario_contrato.js` (`reformatear`, `formatearRut`, `digitoVerificador`, `rutValido`, `iniciarRut`)
- `maestros/models.py` (`Contraparte.identificador_visible`)

**Para mostrar con puntos (Python):**

```python
FORMATO_RUT = r"^\d{7,8}-[\dK]$"

def formatear_rut(valor):
    """`12345678-5` → `12.345.678-5` para mostrar; deja igual lo que no sea un RUT."""
    rut = normalizar_rut(valor)
    if not re.match(FORMATO_RUT, rut):
        return valor
    cuerpo, dv = rut.split("-")
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{dv}"
```

Exponerlo como propiedad del modelo (p. ej. `Residente.rut_visible`) y no como filtro importado en las vistas. Así las tablas, fichas y PDF usan lo mismo.

**Formato en vivo (JS), lo esencial:**

```js
// Reescribe el valor y deja el cursor tras el mismo carácter significativo.
function reformatear(entrada, formatear, esSignificativo) {
  const cursor = entrada.selectionStart ?? entrada.value.length;
  const antes = [...entrada.value.slice(0, cursor)].filter(esSignificativo).length;
  const nuevo = formatear(entrada.value);
  if (nuevo === entrada.value) return;
  entrada.value = nuevo;
  let posicion = 0;
  for (let vistos = 0; posicion < nuevo.length && vistos < antes; posicion++) {
    if (esSignificativo(nuevo[posicion])) vistos++;
  }
  entrada.setSelectionRange(posicion, posicion);
}

const miles = (digitos) => digitos.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

function formatearRut(texto) {
  const limpio = texto.replace(/[^\dkK]/g, "").toUpperCase().slice(0, 9);
  if (limpio.length < 2) return limpio;
  return miles(limpio.slice(0, -1).replace(/K/g, "")) + "-" + limpio.slice(-1);
}

function digitoVerificador(cuerpo) {
  let suma = 0;
  let factor = 2;
  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += Number(cuerpo[i]) * factor;
    factor = factor === 7 ? 2 : factor + 1;
  }
  const resto = 11 - (suma % 11);
  return { 11: "0", 10: "K" }[resto] ?? String(resto);
}

// null mientras está incompleto; true/false cuando ya se puede validar.
function rutValido(texto) {
  const limpio = texto.replace(/[^\dkK]/g, "").toUpperCase();
  if (limpio.length < 8) return null;
  const cuerpo = limpio.slice(0, -1);
  return /^\d+$/.test(cuerpo) && digitoVerificador(cuerpo) === limpio.slice(-1);
}

// Uso: entrada.addEventListener("input", () => reformatear(entrada, formatearRut, (c) => /[\dkK]/.test(c)));
```

En CondoHub el RUT aparece en registro, perfil, residentes y proveedores. Conviene un único `static/js/rut.js` que se active con un atributo (`data-rut`) en cualquier input, en vez de buscar ids concretos.

## 4. Montos con puntos de miles y prefijo de moneda

**Problema que resolvió:** «1250000» es difícil de leer y verificar. Además, el usuario chileno escribe «1.250.000», que Django rechazaba como número.

**Patrón:**
- **Widget de texto** (`TextInput`), no `NumberInput`, para poder mostrar puntos. Lleva `inputmode="decimal"` (o `"numeric"` si no hay decimales), que en el celular abre el teclado numérico.
- **Un campo de formulario** (`MontoField`) que **normaliza antes de validar**: quita `$`, espacios y puntos, y cambia la coma decimal por punto.
- **El widget muestra el valor guardado ya formateado** (`format_value`). Si el formulario vuelve con un error, el monto sigue legible.
- **El prefijo** (`$`) va en un `input-group` de Bootstrap, no dentro del texto.
- **El JS formatea mientras se escribe**, con el mismo `reformatear` del RUT.

**Origen:**
- `contratos/formato.py` (`normalizar_monto`, `formatear_monto`)
- `contratos/formularios.py` (`MontoInput`, `MontoField`)
- JS `formatearMonto` e `iniciarMontos`

**Adaptación a CondoHub.** Los montos son `PositiveIntegerField` en pesos (gastos comunes, egresos, fondo de reserva), así que basta la versión entera:

```python
def normalizar_monto(texto):
    """`$ 1.250.000` → `1250000`."""
    return "".join((texto or "").split()).replace("$", "").replace(".", "")


def formatear_monto(valor):
    return "" if valor is None else f"{int(valor):,}".replace(",", ".")


class MontoInput(forms.TextInput):
    def __init__(self, attrs=None):
        base = {"inputmode": "numeric", "autocomplete": "off", "placeholder": "Ej.: 85.000", "data-monto": ""}
        super().__init__({**base, **(attrs or {})})

    def format_value(self, value):
        return formatear_monto(value) if isinstance(value, int) else super().format_value(value)


class MontoField(forms.IntegerField):
    widget = MontoInput

    def to_python(self, value):
        return super().to_python(normalizar_monto(value) if isinstance(value, str) else value)
```

**En formularios y vistas:**
- En los `ModelForm`: `field_classes = {"monto": MontoField}`.
- En la plantilla: `{% include "_campo.html" with campo=form.monto prefijo="$" %}`.
- Para mostrar en tablas y PDF: una propiedad `monto_visible` o un filtro `|pesos` que use `formatear_monto`. Así no hay tres formatos distintos de dinero en la app.

**Si algún día hay UF:** el contrato usa `de_moneda` + `SIMBOLO_MONEDA` + `DECIMALES_MONEDA`. Al cambiar la moneda, el JS cambia el prefijo y el ejemplo, y el modelo rechaza decimales en pesos («Los montos en pesos no llevan decimales.»).

## 5. Panel principal con tarjetas por estado

**Problema que resolvió:** el panel no decía cuántos contratos había en cada situación ni llevaba a ellos.

**Patrón:**
- **Una tarjeta (`.kpi`) por estado:** nombre, cantidad grande y una frase que explica el estado («Fecha de referencia en 60 días o menos»).
- **La tarjeta entera es un enlace** al listado ya filtrado (`?estado=vencido`).
- **Color por estado en una sola variable CSS** (`--kpi-acento`). Se pinta el borde superior y un punto junto al nombre. El color nunca va solo: siempre hay texto.
- **Grilla de Bootstrap** que pasa de 2 a 3 y a 6 columnas (`row-cols-2 row-cols-md-3 row-cols-xxl-6`), probada para que en 1440 px quepan en una fila.
- **Una tabla de «qué significa cada estado»** al lado, con los mismos colores.

**Origen:**
- `interfaz/templates/interfaz/inicio.html`
- `interfaz/views.py` (`TEXTO_TARJETA`, `DESCRIPCION_ESTADOS`)
- CSS `.kpi`, `.kpi-*`, `.punto-estado`, `.punto-*`

**En CondoHub sirve para:**
- **Administrador:** unidades al día, con deuda y morosas; incidentes abiertos o en curso; reservas pendientes.
- **Comité:** rendición del mes.

Los textos y cantidades se arman en la vista; la plantilla solo los recorre.

```css
.kpi { --kpi-acento: var(--kpi-todos); display: flex; flex-direction: column; gap: .375rem;
       padding: 1rem 1.125rem; border-top: 3px solid var(--kpi-acento); text-decoration: none; }
.kpi:hover, .kpi:focus-visible { border-color: var(--kpi-acento); box-shadow: 0 .25rem .75rem rgba(0,0,0,.08); }
.kpi-moroso { --kpi-acento: var(--kpi-moroso); }   /* uno por estado */
.kpi-valor { font-size: 2rem; font-weight: 700; line-height: 1.1; }
.kpi-texto { font-size: .75rem; color: var(--bs-secondary-color); }
```

## 6. Listado con filtros, chips por estado y búsqueda predictiva

**Problema que resolvió:** encontrar un contrato entre cientos y saber de un vistazo cuáles requieren acción.

**Patrón:**
- **Chips de estado** sobre la tabla, cada uno con su cantidad. El activo lleva `aria-current="true"`, y la cantidad lleva texto oculto para lectores («12 contratos»).
- **Filtros por GET** (tipo, rol, criticidad), con un botón «Limpiar filtros» que aparece solo si hay alguno. Así la URL se puede compartir y el botón Atrás funciona.
- **Búsqueda predictiva** con el patrón *combobox* de ARIA 1.2:
  - sugerencias desde los 2 caracteres, con una espera de 250 ms;
  - navegación con flechas, Enter y Escape;
  - estado anunciado con `aria-live`.
  - Sin JS, Enter envía el formulario y filtra igual.
- **Orden por urgencia:** primero lo que requiere acción y al final lo cerrado o terminado. No es orden alfabético.
- **Etiquetas pequeñas** para lo crítico (`.etiqueta-criticidad-alta`) e insignias de estado (`.insignia-*`) con borde, fondo suave y texto oscuro del mismo tono. Hay que comprobar el contraste AA al elegir los colores de CondoHub.
- **Aislamiento:** el listado y las sugerencias salen del mismo queryset ya filtrado por permisos del usuario. Nunca de `Modelo.objects.all()`.

**Origen:**
- `contratos/templates/contratos/inventario.html`
- `contratos/inventario.py` (`FiltroInventario`, `filas_inventario`, orden)
- `contratos/static/contratos/busqueda_inventario.js`
- `contratos/vistas.py` (`Sugerencias`, JSON acotado)

**En CondoHub:** el listado de unidades o residentes (buscar por número de depto, nombre o RUT), los incidentes y los egresos. Para filtrar por condominio, el aislamiento equivale a la filial de contratos: cada consulta parte del condominio del usuario.

## 7. Ficha de detalle

**Patrón:**
- **Datos en una lista `<dl>`** de dos columnas, con montos y RUT ya formateados (`monto_visible`, `identificador_visible`).
- **Acciones según el estado:**
  - con término registrado: «Registrar término anticipado» pasa a «Corregir término» y se oculta «Nueva vigencia»;
  - las acciones de otros perfiles no se muestran.
- **Aviso destacado** (`.aviso-termino`, con borde izquierdo de color) cuando el registro está cerrado. Explica qué significa: «no se enviarán más avisos».
- **Acciones de cambio por POST** con su propia pantalla, validación y redirección (PRG), más un mensaje de éxito con `messages`.

**Origen:**
- `contratos/templates/contratos/ficha.html`
- `contratos/templates/contratos/termino.html`
- `contratos/vistas.py` (`TerminoAnticipado`)

## 8. Accesibilidad y verificación

**Reglas aplicadas en todas las pantallas:**
- Cada control tiene un `<label for>`. Las ayudas y errores se enlazan con `aria-describedby` y los inválidos llevan `aria-invalid`.
- Placeholder con contraste suficiente: `.form-control::placeholder { color: #6c757d; opacity: 1; }`. El de Bootstrap es demasiado claro.
- Íconos decorativos con `aria-hidden="true"`. Los mensajes que cambian solos van en `aria-live="polite"`.
- Grupos de opciones en `<fieldset>`/`<legend>`. Las tablas usan `<th scope>`.
- El color nunca es el único indicador: el punto de color siempre va con el nombre del estado.

**Cómo se verificó.** No bastó con mirar capturas. Se midieron los rectángulos reales del DOM para detectar:
- textos cortados (`scrollWidth > clientWidth`);
- solapes entre elementos;
- desbordes horizontales en 1440 px y en 375 px (celular).

La captura queda solo para confirmar. El script está en `.claude/skills/verificar-ui/scripts/medir_layout.js` del repo de contratos y sirve tal cual en CondoHub.

**Pruebas que acompañaron cada mejora (pytest):**
- formato y normalización de montos y RUT, parametrizadas;
- un POST con «1.250.000» que se guarda como 1250000;
- un formulario que vuelve con error y conserva el monto formateado;
- la página del formulario contiene las ayudas clave;
- cada vista nueva tiene su prueba de aislamiento (otro condominio → 404).

## 9. Plan sugerido para CondoHub

Ordenado por impacto y esfuerzo. Un issue por fila.

| # | Mejora | Esfuerzo | Depende de |
|---|---|---|---|
| 1 | Componente `_campo.html` + filtro `control` + placeholder con contraste | Bajo | — |
| 2 | Ayudas en los formularios principales (`labels`, `help_texts`, ejemplos en `placeholder`, «Opcional.») | Bajo | 1 |
| 3 | RUT: `formatear_rut`, `rut_visible` y `static/js/rut.js` con `data-rut` | Medio | 1 |
| 4 | Montos: `MontoField`, prefijo `$`, `|pesos` en tablas y PDF | Medio | 1 |
| 5 | Formularios largos en secciones numeradas con frase de introducción | Bajo | 1, 2 |
| 6 | Tarjetas por estado en el panel del administrador | Medio | — |
| 7 | Chips, filtros por GET y orden por urgencia en los listados | Medio | 6 (colores) |
| 8 | Búsqueda predictiva en unidades o residentes | Alto | 7 |

## 10. Qué no copiar

- **Marca y colores de Tattersall** (`--tt-*`, logos, tipografías). CondoHub usa los suyos; solo se trae la estructura de variables.
- **Reglas de negocio de contratos:** estados de vencimiento, avisos 90/60/30/15/7/1, término anticipado, criticidad.
- **Infraestructura de Tattersall:** Azure Blob con cuarentena, Entra ID, Graph.
- **Datos reales:** solo ejemplos ficticios en placeholders, pruebas y datos demo, nunca datos reales.
