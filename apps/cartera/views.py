"""
Vistas de cartera: lo que debe cada condominio asignado a un administrador general (Issue #54, RF18 y RF20).

  - `CarteraView`        /cartera/?mes=AAAA-MM          una fila por condominio, con totales
  - `CarteraCsvView`     /cartera/csv/?mes=AAAA-MM      la misma tabla en CSV para Excel
  - `ReporteCarteraView` /cartera/<pk>/reporte/         el reporte de recaudación de UN condominio, en modo consulta
  - `ReporteCarteraCsvView`                              y su CSV

Todas parten de `condominios_de_cartera` (permisos.py): un condominio no asignado da 404 y quien no tiene cartera, 403.
Ninguna muestra nombres ni RUT de residentes (RNF08) ni cambia el condominio activo de la sesión.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from apps.core.exportar import porcentaje_csv, respuesta_csv
from apps.gastos.views import ReporteBase, ReporteCsvBase, ReportePaginaBase

from .consolidado import armar_cartera, meses_disponibles
from .forms import FiltroMesForm, clave_mes, leer_mes, nombre_mes
from .permisos import CarteraRequeridaMixin


class MesCarteraMixin(CarteraRequeridaMixin):
    """Elige el mes de `?mes=AAAA-MM` (el más reciente con períodos emitidos si falta o no sirve) y arma la cartera."""

    def preparar_cartera(self):
        """Deja en self: disponibles, elegido ((año, mes) o None) y cartera (o None si no hay períodos)."""
        self.disponibles = meses_disponibles(self.condominios)
        self.elegido = leer_mes(self.request.GET.get("mes", ""), self.disponibles)
        if self.elegido is None and self.disponibles:
            self.elegido = self.disponibles[0]
        self.cartera = armar_cartera(self.condominios, *self.elegido) if self.elegido else None


class CarteraView(MesCarteraMixin, TemplateView):
    template_name = "cartera/cartera.html"

    def get_context_data(self, **kwargs):
        self.preparar_cartera()
        contexto = super().get_context_data(**kwargs)
        clave = clave_mes(*self.elegido) if self.elegido else ""
        contexto.update(
            cartera=self.cartera,
            form=FiltroMesForm(initial={"mes": clave}, disponibles=self.disponibles),
            clave_mes=clave,
            nombre_mes=nombre_mes(*self.elegido) if self.elegido else "",
        )
        return contexto


class CarteraCsvView(MesCarteraMixin, View):
    """Descarga la cartera del mes en CSV: una fila por condominio y la de totales, como en la página."""

    ENCABEZADOS = ["Condominio", "Período", "Total emitido", "Total recaudado", "% de recaudación",
                   "Deuda anterior", "Unidades morosas"]

    def get(self, request, *args, **kwargs):
        self.preparar_cartera()
        if self.cartera is None:
            messages.error(request, "Todavía no hay períodos emitidos para descargar.")
            return redirect("cartera:inicio")
        cartera = self.cartera
        filas = [self.fila_csv(fila) for fila in cartera.filas]
        filas.append(
            ["Total", nombre_mes(cartera.anio, cartera.mes), cartera.total_emitido, cartera.total_recaudado,
             porcentaje_csv(cartera.porcentaje_recaudacion), cartera.deuda_anterior, cartera.unidades_morosas]
        )
        return respuesta_csv(f"cartera-{clave_mes(cartera.anio, cartera.mes)}.csv", self.ENCABEZADOS, filas)

    def fila_csv(self, fila):
        if not fila.tiene_periodo:
            return [fila.condominio.nombre, "Sin período emitido", "", "", "", "", ""]
        return [fila.condominio.nombre, str(fila.periodo), fila.emitido, fila.recaudado,
                porcentaje_csv(fila.porcentaje_recaudacion), fila.deuda_anterior, fila.unidades_morosas]


class CondominioDeCarteraMixin(CarteraRequeridaMixin, ReporteBase):
    """El reporte es del condominio de la URL, si está en la cartera (si no, 404). La sesión no cambia."""

    def get_condominio_reporte(self):
        if not hasattr(self, "_condominio_reporte"):
            self._condominio_reporte = get_object_or_404(self.condominios, pk=self.kwargs["pk"])
        return self._condominio_reporte

    def get_url_reporte(self):
        return reverse("cartera:reporte", args=[self.get_condominio_reporte().pk])

    def get_url_csv(self):
        return reverse("cartera:reporte_csv", args=[self.get_condominio_reporte().pk])


class ReporteCarteraView(CondominioDeCarteraMixin, ReportePaginaBase, TemplateView):
    def get_migas(self):
        """Vuelve a la cartera del mes del reporte que se está viendo."""
        enlace = reverse("cartera:inicio")
        if self.reporte:
            enlace += f"?mes={clave_mes(self.reporte.periodo.anio, self.reporte.periodo.mes)}"
        return [("Cartera", enlace)]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["condominio_consulta"] = self.get_condominio_reporte()
        return contexto


class ReporteCarteraCsvView(CondominioDeCarteraMixin, ReporteCsvBase, View):
    """El CSV del reporte de un condominio de la cartera (el mismo archivo que ve su administrador)."""
