"""Rutas de gastos comunes (prefijo /gastos/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "gastos"

urlpatterns = [
    path("fondo/", views.FondoListView.as_view(), name="fondo"),
    path("fondo/inicial/", views.FondoCreateView.as_view(tipo="INICIAL"), name="fondo_inicial"),
    path("fondo/egreso/", views.FondoCreateView.as_view(tipo="EGRESO"), name="fondo_egreso"),
    path("fondo/ajuste/", views.FondoCreateView.as_view(tipo="AJUSTE"), name="fondo_ajuste"),
    path("fondo/<int:pk>/", views.FondoDetailView.as_view(), name="fondo_detalle"),
    path("", views.PeriodoListView.as_view(), name="periodos"),
    path("periodos/nuevo/", views.PeriodoCreateView.as_view(), name="periodo_nuevo"),
    path("periodos/<int:pk>/", views.PeriodoDetailView.as_view(), name="periodo_detalle"),
    path("periodos/<int:pk>/editar/", views.PeriodoUpdateView.as_view(), name="periodo_editar"),
    path("periodos/<int:pk>/emitir/", views.EmitirPeriodoView.as_view(), name="periodo_emitir"),
    path("periodos/<int:periodo_pk>/egresos/nuevo/", views.EgresoCreateView.as_view(), name="egreso_nuevo"),
    path("egresos/<int:pk>/editar/", views.EgresoUpdateView.as_view(), name="egreso_editar"),
    path("egresos/<int:pk>/eliminar/", views.EgresoDeleteView.as_view(), name="egreso_eliminar"),
    # Ítems de cobro (RQ-02, #117): cuotas extraordinarias, multas...
    path("periodos/<int:periodo_pk>/items/nuevo/", views.ItemCobroCreateView.as_view(), name="item_nuevo"),
    path("items/<int:pk>/editar/", views.ItemCobroUpdateView.as_view(), name="item_editar"),
    path("items/<int:pk>/eliminar/", views.ItemCobroDeleteView.as_view(), name="item_eliminar"),
    # Reporte de morosidad (Issue #5): los filtros van en la URL (?periodo=..&edificio=..)
    path("reporte/", views.ReporteView.as_view(), name="reporte"),
    path("reporte/csv/", views.ReporteCsvView.as_view(), name="reporte_csv"),
]
