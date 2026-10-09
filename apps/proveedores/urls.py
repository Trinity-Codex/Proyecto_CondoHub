"""Rutas de proveedores (prefijo /proveedores/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "proveedores"

urlpatterns = [
    path("", views.ProveedorListView.as_view(), name="lista"),
    path("nuevo/", views.ProveedorCreateView.as_view(), name="nuevo"),
    path("<int:pk>/editar/", views.ProveedorUpdateView.as_view(), name="editar"),
    path("<int:pk>/estado/", views.ProveedorCambiarEstadoView.as_view(), name="estado"),
]