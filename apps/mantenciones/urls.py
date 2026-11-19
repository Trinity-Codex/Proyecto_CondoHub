"""Rutas de mantenciones (prefijo /mantenciones/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "mantenciones"

urlpatterns = [
    path("", views.MantencionListView.as_view(), name="lista"),
    path("nueva/", views.MantencionCreateView.as_view(), name="nueva"),
    path("<int:pk>/editar/", views.MantencionUpdateView.as_view(), name="editar"),
    path("<int:pk>/ejecucion/", views.EjecucionCreateView.as_view(), name="ejecucion"),
    path("ejecuciones/<int:pk>/certificado/", views.CertificadoView.as_view(), name="certificado"),
]
