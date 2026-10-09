"""Rutas de pagos y estado de cuenta (prefijo /pagos/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("mi-cuenta/", views.EstadoCuentaView.as_view(), name="estado_cuenta"),
    path("mi-cuenta/<int:pk>/", views.CobroDetailView.as_view(), name="cobro_detalle"),
]