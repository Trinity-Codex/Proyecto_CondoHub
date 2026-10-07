"""Rutas de gastos comunes (prefijo /gastos/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "gastos"

urlpatterns = [
    path("", views.PeriodoListView.as_view(), name="periodos"),
    path("periodos/nuevo/", views.PeriodoCreateView.as_view(), name="periodo_nuevo"),
    path("periodos/<int:pk>/", views.PeriodoDetailView.as_view(), name="periodo_detalle"),
    path("periodos/<int:pk>/editar/", views.PeriodoUpdateView.as_view(), name="periodo_editar"),
    path("periodos/<int:periodo_pk>/egresos/nuevo/", views.EgresoCreateView.as_view(), name="egreso_nuevo"),
    path("egresos/<int:pk>/editar/", views.EgresoUpdateView.as_view(), name="egreso_editar"),
    path("egresos/<int:pk>/eliminar/", views.EgresoDeleteView.as_view(), name="egreso_eliminar"),
]
