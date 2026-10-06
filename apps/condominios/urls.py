"""Rutas de condominios (prefijo /condominio/)."""
from django.urls import path

from . import views

app_name = "condominios"

urlpatterns = [
    path("unidades/", views.UnidadesView.as_view(), name="unidades"),
]
