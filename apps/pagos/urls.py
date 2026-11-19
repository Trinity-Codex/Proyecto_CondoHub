"""Rutas de pagos y estado de cuenta (prefijo /pagos/ en config/urls.py)."""
from django.urls import path

from . import views
from .aviso import AvisoCobroView

app_name = "pagos"

urlpatterns = [
    # Residente
    path("mi-cuenta/", views.EstadoCuentaView.as_view(), name="estado_cuenta"),
    path("mi-cuenta/<int:pk>/", views.CobroDetailView.as_view(), name="cobro_detalle"),
    path("cobro/<int:pk>/aviso.pdf", AvisoCobroView.as_view(), name="aviso_cobro"),
    # Administración
    path("cobranza/", views.CobranzaView.as_view(), name="cobranza"),
    path("unidad/<int:pk>/", views.CuentaUnidadView.as_view(), name="cuenta_unidad"),
    path("cobro/<int:pk>/pago/", views.RegistrarPagoView.as_view(), name="registrar_pago"),
    path("pago/<int:pk>/anular/", views.AnularPagoView.as_view(), name="anular_pago"),
]
