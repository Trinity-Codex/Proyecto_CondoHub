"""Rutas de incidentes (prefijo /incidentes/)."""
from django.urls import path

from . import views

app_name = "incidentes"

urlpatterns = [
    path("", views.IncidenteListView.as_view(), name="lista"),
    path("nuevo/", views.IncidenteCreateView.as_view(), name="nuevo"),
    path("<int:pk>/", views.IncidenteDetailView.as_view(), name="detalle"),
]
