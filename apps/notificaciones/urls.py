"""Rutas de notificaciones (prefijo /notificaciones/)."""
from django.urls import path

from . import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.NotificacionListView.as_view(), name="lista"),
    path("<int:pk>/abrir/", views.abrir, name="abrir"),
    path("marcar-todas-leidas/", views.marcar_todas_leidas, name="marcar_todas_leidas"),
]
