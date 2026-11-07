"""Rutas de rendicion (prefijo /rendicion/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "rendicion"

urlpatterns = [
    path("", views.RendicionInicioView.as_view(), name="inicio"),
]
