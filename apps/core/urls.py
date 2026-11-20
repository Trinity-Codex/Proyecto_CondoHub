"""Rutas generales del sitio."""
from django.urls import path
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("sw.js", never_cache(TemplateView.as_view(
        template_name="core/sw.js", content_type="application/javascript",
    )), name="service_worker"),
    path("", views.InicioView.as_view(), name="inicio"),
    path("cambiar-condominio/<int:pk>/", views.cambiar_condominio, name="cambiar_condominio"),
    path("sin-condominio/", views.sin_condominio, name="sin_condominio"),
]
