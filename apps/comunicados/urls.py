"""Rutas de comunicados (prefijo /comunicados/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "comunicados"

urlpatterns = [
    path("", views.ComunicadoListView.as_view(), name="lista"),
    path("nuevo/", views.ComunicadoCreateView.as_view(), name="nuevo"),
    path("<int:pk>/", views.ComunicadoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ComunicadoUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ComunicadoDeleteView.as_view(), name="eliminar"),
]
