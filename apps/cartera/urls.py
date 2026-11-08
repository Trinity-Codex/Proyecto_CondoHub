"""Rutas de cartera (prefijo /cartera/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "cartera"

urlpatterns = [
    path("", views.CarteraInicioView.as_view(), name="inicio"),
]
