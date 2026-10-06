"""Rutas generales del sitio."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("cambiar-condominio/<int:pk>/", views.cambiar_condominio, name="cambiar_condominio"),
    path("sin-condominio/", views.sin_condominio, name="sin_condominio"),
]
