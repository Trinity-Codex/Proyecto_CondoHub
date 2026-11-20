"""Rutas de incidentes (prefijo /incidentes/)."""
from django.urls import path

from . import views

app_name = "incidentes"

urlpatterns = [
    path("", views.IncidenteListView.as_view(), name="lista"),
    path("nuevo/", views.IncidenteCreateView.as_view(), name="nuevo"),
    path("<int:pk>/", views.IncidenteDetailView.as_view(), name="detalle"),
    # Fotos de respaldo (Issue #122): el archivo se entrega por la vista, no por MEDIA_URL.
    path("<int:pk>/fotos/", views.FotoSubirView.as_view(), name="foto_subir"),
    path("fotos/<int:pk>/", views.FotoArchivoView.as_view(), name="foto"),
    path("fotos/<int:pk>/borrar/", views.FotoBorrarView.as_view(), name="foto_borrar"),
]
