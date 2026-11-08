"""Rutas de privacidad (prefijo /privacidad/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "privacidad"

urlpatterns = [
    path("", views.AvisoPrivacidadView.as_view(), name="aviso"),
    path("mis-datos/", views.DescargarMisDatosView.as_view(), name="descargar"),
    # Solicitudes del titular: las de la persona...
    path("mis-solicitudes/", views.MisSolicitudesView.as_view(), name="mis_solicitudes"),
    path("mis-solicitudes/nueva/", views.SolicitudCreateView.as_view(), name="solicitud_nueva"),
    path("mis-solicitudes/<int:pk>/", views.SolicitudDetailView.as_view(), name="solicitud"),
    # ...y las del condominio, para el administrador.
    path("solicitudes/", views.SolicitudesView.as_view(), name="solicitudes"),
    path("solicitudes/<int:pk>/", views.ResponderSolicitudView.as_view(), name="responder"),
]
