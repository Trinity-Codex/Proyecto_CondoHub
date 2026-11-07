"""Rutas de privacidad (prefijo /privacidad/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "privacidad"

urlpatterns = [
    path("", views.AvisoPrivacidadView.as_view(), name="aviso"),
]
