"""Rutas de condominios (prefijo /condominio/)."""
from django.urls import path

from . import views

app_name = "condominios"

urlpatterns = [
    path("unidades/", views.UnidadesView.as_view(), name="unidades"),
    # Edificios
    path("edificios/nuevo/", views.EdificioCreateView.as_view(), name="edificio_nuevo"),
    path("edificios/<int:pk>/editar/", views.EdificioUpdateView.as_view(), name="edificio_editar"),
    path("edificios/<int:pk>/eliminar/", views.EdificioDeleteView.as_view(), name="edificio_eliminar"),
    # Unidades
    path("unidades/nueva/", views.UnidadCreateView.as_view(), name="unidad_nueva"),
    path("unidades/<int:pk>/editar/", views.UnidadUpdateView.as_view(), name="unidad_editar"),
    path("unidades/<int:pk>/eliminar/", views.UnidadDeleteView.as_view(), name="unidad_eliminar"),
    # Residentes
    path("unidades/<int:unidad_pk>/residentes/nuevo/", views.ResidenteCreateView.as_view(), name="residente_nuevo"),
    path("residentes/<int:pk>/baja/", views.ResidenteBajaView.as_view(), name="residente_baja"),
]
