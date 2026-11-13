"""Rutas de cartera (prefijo /cartera/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "cartera"

urlpatterns = [
    path("", views.CarteraView.as_view(), name="inicio"),
    path("csv/", views.CarteraCsvView.as_view(), name="csv"),
    path("<int:pk>/reporte/", views.ReporteCarteraView.as_view(), name="reporte"),
    path("<int:pk>/reporte/csv/", views.ReporteCarteraCsvView.as_view(), name="reporte_csv"),
]
