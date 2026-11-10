"""
Vistas de gastos comunes: períodos y egresos (Issue #1, RF02).

Permisos:
  - Ver períodos y egresos:                         administrador y comité
  - Abrir períodos y crear/editar/eliminar egresos: administrador
  - Residentes y conserje:                          sin acceso (403)

Los egresos solo se modifican mientras el período está ABIERTO. Una vez
EMITIDO (Issue #2) quedan bloqueados: cambiarlos descuadraría lo ya cobrado.

Emitir (solo administrador): EmitirPeriodoView muestra una vista previa con
lo que pagará cada unidad y, al confirmar, usa servicios.emitir_periodo().

Reporte de morosidad (Issue #5, administrador y comité): ReporteView lo muestra
y ReporteCsvView lo descarga para Excel. El cálculo está en reportes.py.
"""
from collections import Counter

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

from apps.core.exportar import celda_segura, porcentaje_csv, respuesta_csv  # noqa: F401  (celda_segura se sigue importando desde aquí)
from apps.core.listados import FiltrosGetMixin, leer_opcion
from apps.core.permisos import ADMINISTRADOR, COMITE, CondominioQuerysetMixin, RolRequeridoMixin
from apps.core.templatetags.condohub import pesos

from .filtros import COLOR_SITUACION, SITUACIONES, ordenar_por_urgencia
from .forms import EgresoForm, FiltroReporteForm, MovimientoFondoForm, PeriodoForm
from .models import Egreso, MovimientoFondo, PeriodoGasto
from .fondo import registrar_movimiento, saldo_fondo
from .reportes import generar_reporte
from .servicios import calcular_emision, emitir_periodo


# --------------------------------------------------------------------------
# Períodos
# --------------------------------------------------------------------------
class PeriodoListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    """Lista de períodos del condominio con su total y cantidad de egresos."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = PeriodoGasto
    template_name = "gastos/periodos.html"
    context_object_name = "periodos"
    paginate_by = 12  # un año por página

    def get_queryset(self):
        # annotate() calcula el total y la cantidad en la misma consulta (no una por período).
        # Con annotate() Django ignora el "ordering" del modelo: hay que repetirlo (más reciente primero).
        return (
            super().get_queryset()
            .annotate(total=Sum("egresos__monto"), cantidad=Count("egresos"))
            .order_by("-anio", "-mes")
        )


class PeriodoFormMixin:
    """Lo que comparten abrir y editar un período."""

    model = PeriodoGasto
    form_class = PeriodoForm
    template_name = "gastos/periodo_formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio
        return kwargs


class PeriodoCreateView(RolRequeridoMixin, PeriodoFormMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]

    def get_initial(self):
        """Por defecto se propone el mes actual."""
        hoy = timezone.localdate()
        return {"mes": hoy.month, "anio": hoy.year}

    def form_valid(self, form):
        form.instance.condominio = self.request.condominio
        messages.success(self.request, f"Período {form.instance} abierto. Ya puedes registrar sus egresos.")
        return super().form_valid(form)  # redirige a get_absolute_url() del período


class PeriodoUpdateView(RolRequeridoMixin, CondominioQuerysetMixin, PeriodoFormMixin, UpdateView):
    """Corregir mes, año o % del fondo de reserva (solo si el período está abierto)."""

    roles_permitidos = [ADMINISTRADOR]

    def get_queryset(self):
        return super().get_queryset().filter(estado=PeriodoGasto.Estado.ABIERTO)  # emitido -> 404

    def form_valid(self, form):
        messages.success(self.request, "Período actualizado.")
        return super().form_valid(form)


class PeriodoDetailView(FiltrosGetMixin, RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    """Detalle del período: egresos (filtrables por categoría), total y subtotal por categoría."""

    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = PeriodoGasto
    template_name = "gastos/periodo_detalle.html"
    context_object_name = "periodo"
    parametros_filtro = {"categoria": Egreso.Categoria.values}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # Una sola consulta da cantidad y subtotal de cada categoría, sobre todos los egresos del período.
        nombres = dict(Egreso.Categoria.choices)
        resumen = list(
            self.object.egresos.order_by().values("categoria").annotate(n=Count("pk"), subtotal=Sum("monto"))
            .order_by("-subtotal")
        )
        total = sum(fila["subtotal"] for fila in resumen)
        categoria = self.filtro("categoria")
        egresos = self.object.egresos.select_related("creado_por", "proveedor")  # orden del modelo: fecha, pk
        if categoria:
            egresos = egresos.filter(categoria=categoria)
        contexto["egresos"] = egresos
        contexto["total"] = total
        contexto["filtrado"] = bool(categoria)
        # Subtotal por categoría, con su nombre legible y su porcentaje del total.
        contexto["por_categoria"] = [
            {
                "categoria": nombres[fila["categoria"]],
                "subtotal": fila["subtotal"],
                "porcentaje": round(fila["subtotal"] * 100 / total, 1) if total else 0,
            }
            for fila in resumen
        ]
        # Chips: solo las categorías que tienen egresos en este período.
        cantidades = {fila["categoria"]: fila["n"] for fila in resumen}
        opciones = [(valor, nombres[valor], "reserva") for valor in Egreso.Categoria.values if valor in cantidades]
        contexto["chips"] = self.chips("categoria", opciones, cantidades, singular="egreso", plural="egresos")
        # Si ya se emitió: lo que paga cada unidad (DetalleGastoComun).
        if not self.object.esta_abierto:
            cobros = self.object.detalles.select_related("unidad__edificio").order_by(
                "unidad__edificio__nombre", "unidad__piso", "unidad__numero"
            )
            contexto["cobros"] = cobros
            contexto["totales_cobros"] = cobros.aggregate(
                gastos=Sum("monto"), fondo=Sum("monto_fondo_reserva")
            )
        return contexto


class EmitirPeriodoView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    """
    Emisión de los gastos comunes del período (Issue #2).

    GET  -> vista previa: cuánto pagará cada unidad, o por qué no se puede emitir.
    POST -> emite: crea los cobros, cierra el período y avisa a los residentes.
    """

    roles_permitidos = [ADMINISTRADOR]
    model = PeriodoGasto
    template_name = "gastos/emitir.html"
    context_object_name = "periodo"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["emision"] = calcular_emision(self.object)
        contexto["estrategia"] = self.object.get_criterio_prorrateo_display()
        return contexto

    def post(self, request, *args, **kwargs):
        periodo = self.get_object()
        try:
            emision = emitir_periodo(periodo, usuario=request.user)
        except ValidationError as error:
            for mensaje in error.messages:
                messages.error(request, mensaje)
            return redirect("gastos:periodo_emitir", pk=periodo.pk)
        messages.success(
            request,
            f"Gastos comunes de {periodo} emitidos: {len(emision.filas)} unidades, "
            f"total a cobrar {pesos(emision.total_a_cobrar)}. Se avisó a los residentes.",
        )
        return redirect(periodo)


# --------------------------------------------------------------------------
# Egresos
# --------------------------------------------------------------------------
class PeriodoAbiertoMixin:
    """
    Bloquea crear, editar o eliminar egresos de un período que ya no está abierto.
    Cada vista define get_periodo() para saber de qué período se trata.
    """

    def dispatch(self, request, *args, **kwargs):
        # RolRequeridoMixin (que va antes en la lista de clases) ya revisó la
        # sesión y el condominio activo; aquí se revisa el estado del período.
        if request.user.is_authenticated and request.condominio is not None:
            periodo = self.get_periodo()
            if not periodo.esta_abierto:
                messages.error(request, f"El período {periodo} ya fue emitido: sus egresos no se pueden modificar.")
                return redirect(periodo)
        return super().dispatch(request, *args, **kwargs)


class EgresoCreateView(RolRequeridoMixin, PeriodoAbiertoMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    model = Egreso
    form_class = EgresoForm
    template_name = "gastos/egreso_formulario.html"

    def get_periodo(self):
        # Solo períodos del condominio activo: el de otro condominio responde 404.
        if not hasattr(self, "_periodo"):
            self._periodo = get_object_or_404(PeriodoGasto, pk=self.kwargs["periodo_pk"], condominio=self.request.condominio)
        return self._periodo

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio  # para ofrecer solo sus proveedores
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["periodo"] = self.get_periodo()
        return contexto

    def form_valid(self, form):
        form.instance.periodo = self.get_periodo()
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Egreso registrado.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_periodo().get_absolute_url()


class EgresoDelPeriodoMixin(CondominioQuerysetMixin):
    """Para editar y eliminar: el egreso debe ser de un período del condominio activo."""

    model = Egreso
    campo_condominio = "periodo__condominio"

    def get_periodo(self):
        return self.get_object().periodo

    def get_success_url(self):
        return self.object.periodo.get_absolute_url()


class EgresoUpdateView(RolRequeridoMixin, EgresoDelPeriodoMixin, PeriodoAbiertoMixin, UpdateView):
    roles_permitidos = [ADMINISTRADOR]
    form_class = EgresoForm
    template_name = "gastos/egreso_formulario.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.request.condominio  # para ofrecer solo sus proveedores
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["periodo"] = self.object.periodo
        return contexto

    def form_valid(self, form):
        messages.success(self.request, "Egreso actualizado.")
        return super().form_valid(form)


class EgresoDeleteView(RolRequeridoMixin, EgresoDelPeriodoMixin, PeriodoAbiertoMixin, DeleteView):
    roles_permitidos = [ADMINISTRADOR]
    template_name = "gastos/egreso_confirmar_eliminar.html"

    def form_valid(self, form):
        messages.success(self.request, "Egreso eliminado.")
        return super().form_valid(form)


# --------------------------------------------------------------------------
# Reporte de gastos comunes y morosidad (Issue #5, RF11)
# --------------------------------------------------------------------------
class ReporteBase:
    """
    Lo que comparten la página del reporte y su descarga en CSV, SIN permisos: leer los filtros de la URL
    (?periodo=..&edificio=..&solo_deuda=on) y generar el reporte de UN condominio.

    Quien la use pone antes su propio control de acceso. `ReporteMixin` (abajo) exige un rol en el condominio
    activo; la cartera (apps/cartera, Issue #54) exige un condominio asignado y entrega el suyo en
    `get_condominio_reporte()`. Las URL de la página y del CSV también son ganchos, para que los enlaces
    y las redirecciones vuelvan a donde se abrió el reporte.
    """

    def get_condominio_reporte(self):
        """El condominio del reporte: por defecto, el condominio activo de la sesión."""
        return self.request.condominio

    def get_url_reporte(self):
        return reverse("gastos:reporte")

    def get_url_csv(self):
        return reverse("gastos:reporte_csv")

    def preparar_reporte(self):
        """Deja en self: form, reporte (o None), filas a mostrar y la consulta para el enlace CSV."""
        condominio = self.get_condominio_reporte()
        datos = self.request.GET.copy()  # copy(): request.GET no se puede modificar
        # Sin período elegido se muestra el último emitido (ordering del modelo: más reciente primero).
        if not datos.get("periodo"):
            ultimo = PeriodoGasto.objects.filter(condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO).first()
            if ultimo:
                datos["periodo"] = ultimo.pk
        self.form = FiltroReporteForm(datos, condominio=condominio)
        self.reporte, self.filas, self.situacion = None, [], ""
        if datos.get("periodo") and self.form.is_valid():
            filtros = self.form.cleaned_data
            self.reporte = generar_reporte(filtros["periodo"], filtros["edificio"])
            # "Solo con deuda" y la situación filtran la TABLA; los totales siguen siendo de todas las unidades.
            # Si llegan las dos, manda la situación (Issue #80). Una situación desconocida se ignora.
            self.situacion = leer_opcion(self.request.GET, "situacion", SITUACIONES)
            if self.situacion:
                self.filas = [f for f in self.reporte.filas if f.situacion == SITUACIONES[self.situacion]]
            else:
                self.filas = self.reporte.unidades_con_deuda if filtros["solo_deuda"] else self.reporte.filas
        self.consulta = datos.urlencode()


class ReporteMixin(RolRequeridoMixin, ReporteBase):
    """El reporte de gastos comunes: administrador y comité, del condominio activo."""

    roles_permitidos = [ADMINISTRADOR, COMITE]


class ReportePaginaBase(FiltrosGetMixin, ReporteBase):
    """La página del reporte, sin permisos. Con `TemplateView` detrás, ver `ReporteView` y la cartera."""

    template_name = "gastos/reporte.html"
    parametros_filtro = {"situacion": list(SITUACIONES)}

    def get_migas(self):
        """Enlaces anteriores de la ruta de migas, como (texto, url); la página actual se agrega sola."""
        return [("Gastos comunes", reverse("gastos:periodos"))]

    def get_context_data(self, **kwargs):
        self.preparar_reporte()
        contexto = super().get_context_data(**kwargs)
        # La tabla va por urgencia (morosas primero); el CSV conserva su orden por edificio y unidad.
        contexto.update(form=self.form, reporte=self.reporte, filas=ordenar_por_urgencia(self.filas),
                        consulta=self.consulta, situacion=self.situacion,
                        migas=self.get_migas(), url_csv=self.get_url_csv())
        if self.reporte:
            # Cantidades del período y edificio elegidos, sin importar la situación ni "solo con deuda".
            cantidades = Counter(fila.situacion for fila in self.reporte.filas)
            opciones = [(clave, texto, COLOR_SITUACION[clave]) for clave, texto in SITUACIONES.items()]
            contexto["chips"] = self.chips(
                "situacion", opciones, {c: cantidades[t] for c, t in SITUACIONES.items()},
                singular="unidad", plural="unidades",
            )
        return contexto


class ReporteView(ReporteMixin, ReportePaginaBase, TemplateView):
    pass


class ReporteCsvBase(ReporteBase):
    """Descarga el reporte en CSV para Excel (`respuesta_csv`), sin permisos. Con `View` detrás."""

    def get(self, request, *args, **kwargs):
        self.preparar_reporte()
        if self.reporte is None:
            messages.error(request, "Elige un período emitido para descargar el reporte.")
            return redirect(f"{self.get_url_reporte()}?{self.consulta}")

        periodo = self.reporte.periodo
        encabezados = ["Edificio", "Unidad", "Período", "Total cobrado", "Pagado", "Saldo del período",
                       "Deuda anterior", "Deuda total", "Situación"]
        filas = [
            [fila.unidad.edificio.nombre, fila.unidad.numero, str(periodo), fila.total, fila.pagado,
             fila.saldo, fila.deuda_anterior, fila.deuda_total, fila.situacion]
            for fila in self.filas
        ]
        r = self.reporte
        # Si se filtró "solo con deuda", la fila Total sigue siendo de todas las unidades: se aclara.
        etiqueta = "Total" if len(self.filas) == len(r.filas) else "Total (todas las unidades)"
        filas.append(
            [etiqueta, "", str(periodo), r.total_emitido, r.total_recaudado, r.saldo_periodo, r.deuda_anterior,
             r.deuda_total, f"{porcentaje_csv(r.porcentaje_recaudacion)} % recaudado"]
        )
        return respuesta_csv(f"morosidad-{periodo.anio}-{periodo.mes:02d}.csv", encabezados, filas)


class ReporteCsvView(ReporteMixin, ReporteCsvBase, View):
    """El CSV del reporte: separador ";" y UTF-8 con BOM (así Excel lee bien las tildes)."""


class FondoListView(RolRequeridoMixin, CondominioQuerysetMixin, ListView):
    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = MovimientoFondo
    template_name = "gastos/fondo.html"
    context_object_name = "movimientos"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("proveedor", "periodo")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        try:
            contexto["saldo"] = saldo_fondo(self.request.condominio)
        except ValidationError as error:
            contexto["aviso_apertura"] = " ".join(error.messages)
        contexto["tiene_inicial"] = self.get_queryset().filter(tipo=MovimientoFondo.Tipo.INICIAL).exists()
        return contexto


class FondoDetailView(RolRequeridoMixin, CondominioQuerysetMixin, DetailView):
    roles_permitidos = [ADMINISTRADOR, COMITE]
    model = MovimientoFondo
    template_name = "gastos/fondo_detalle.html"
    context_object_name = "movimiento"

    def get_queryset(self):
        return super().get_queryset().select_related("proveedor", "periodo", "creado_por")


class FondoCreateView(RolRequeridoMixin, CondominioQuerysetMixin, CreateView):
    roles_permitidos = [ADMINISTRADOR]
    model = MovimientoFondo
    form_class = MovimientoFondoForm
    template_name = "gastos/fondo_formulario.html"
    tipo = MovimientoFondo.Tipo.INICIAL

    def get_initial(self):
        return {"fecha": timezone.localdate()}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("instance", None)
        return {**kwargs, "condominio": self.request.condominio, "tipo": self.tipo}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "titulo": dict(MovimientoFondo.Tipo.choices)[self.tipo]}

    def form_valid(self, form):
        datos = form.cleaned_data.copy()
        sentido = datos.pop("sentido", "SUMAR")
        if sentido == "RESTAR":
            datos["monto"] = -datos["monto"]
        try:
            self.object = registrar_movimiento(self.request.condominio, tipo=self.tipo, usuario=self.request.user, **datos)
        except ValidationError as error:
            if hasattr(error, "error_dict"):
                for campo, errores in error.error_dict.items():
                    form.add_error(campo if campo in form.fields else None, errores)
            else:
                form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Movimiento del fondo registrado.")
        return redirect(self.object)
