"""
Filtros por GET y chips de estado de los listados (Issue #80).

Un listado declara los parámetros que acepta y sus valores válidos:

    class MiLista(FiltrosGetMixin, ListView):
        parametros_filtro = {"estado": Incidente.Estado.values}

y arma los chips con las cantidades que ya calculó sobre su queryset acotado por condominio y rol:

    contexto["chips"] = self.chips("estado", opciones, cantidades, ...)

Reglas:
  - Un valor desconocido se ignora (no hay error): `leer_opcion` devuelve "".
  - Los enlaces de los chips y de la paginación conservan el resto de la URL y quitan `page`.
  - «Limpiar filtros» quita solo los parámetros de filtro (y `page`).
  - `q` (búsqueda, Issue #82) queda reservado: se conserva en los enlaces y «Limpiar filtros» lo quita,
    pero todavía no cuenta como filtro activo ni se interpreta aquí.
"""
PARAMETRO_BUSQUEDA = "q"
PARAMETRO_PAGINA = "page"


def leer_opcion(get, nombre, validos):
    """El valor de `?nombre=` si está entre `validos`; si no, "" (se ignora)."""
    valor = get.get(nombre, "")
    return valor if valor in validos else ""


def _conservados(get, parametros_filtro):
    """Copia de la consulta sin `page` y sin los filtros de valor desconocido."""
    consulta = get.copy()
    consulta.pop(PARAMETRO_PAGINA, None)
    for nombre, validos in parametros_filtro.items():
        if nombre in consulta and consulta.get(nombre) not in validos:
            consulta.pop(nombre)
    return consulta


def _enlace(consulta):
    texto = consulta.urlencode()
    return f"?{texto}" if texto else "?"


def parametros_de_url(get, parametros_filtro):
    """`filtros_url` de `_paginacion.html`: lo que se conserva al cambiar de página (sin `page`)."""
    return _conservados(get, parametros_filtro).urlencode()


def hay_filtros(get, parametros_filtro):
    return any(leer_opcion(get, nombre, validos) for nombre, validos in parametros_filtro.items())


def url_limpiar(get, parametros_filtro):
    """Quita los filtros (y `q`) y conserva lo demás, como `periodo` y `edificio` del reporte."""
    consulta = _conservados(get, parametros_filtro)
    for nombre in (*parametros_filtro, PARAMETRO_BUSQUEDA):
        consulta.pop(nombre, None)
    return _enlace(consulta)


def armar_chips(get, parametros_filtro, parametro, opciones, cantidades, *, singular, plural, total=None):
    """
    Lista de chips para `templates/_chips.html`: «Todos» y uno por opción.

    `opciones`: iterable de (valor, texto, clave_color). `cantidades`: dict valor -> cantidad.
    `total`: cantidad de «Todos» (por defecto, la suma de las cantidades).
    """
    actual = leer_opcion(get, parametro, parametros_filtro[parametro])
    base = _conservados(get, parametros_filtro)

    def chip(valor, texto, cantidad, clave_color):
        consulta = base.copy()
        if valor:
            consulta[parametro] = valor
        else:
            consulta.pop(parametro, None)
        return {
            "valor": valor, "texto": texto, "cantidad": cantidad, "clave_color": clave_color,
            "descripcion": f"{cantidad} {singular if cantidad == 1 else plural}",
            "url": _enlace(consulta), "activo": valor == actual,
        }

    opciones = list(opciones)
    if total is None:
        total = sum(cantidades.get(valor, 0) for valor, _, _ in opciones)
    return [chip("", "Todos", total, "reserva")] + [
        chip(valor, texto, cantidades.get(valor, 0), color) for valor, texto, color in opciones
    ]


class FiltrosGetMixin:
    """
    Para vistas de clase (ListView, DetailView, TemplateView): lee los filtros declarados en
    `parametros_filtro` ({nombre: valores válidos}) y deja en el contexto `filtros_url`, `hay_filtros`
    y `url_limpiar`.
    """

    parametros_filtro = {}

    def filtro(self, nombre):
        return leer_opcion(self.request.GET, nombre, self.parametros_filtro[nombre])

    def chips(self, parametro, opciones, cantidades, **kwargs):
        return armar_chips(self.request.GET, self.parametros_filtro, parametro, opciones, cantidades, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        get = self.request.GET
        contexto.update(
            filtros_url=parametros_de_url(get, self.parametros_filtro),
            hay_filtros=hay_filtros(get, self.parametros_filtro),
            url_limpiar=url_limpiar(get, self.parametros_filtro),
        )
        return contexto
