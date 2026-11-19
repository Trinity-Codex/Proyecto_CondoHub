"""Rutas de comunicados (prefijo /comunicados/ en config/urls.py)."""
from django.urls import path

from . import views

app_name = "comunicados"

urlpatterns = [
    path("", views.ComunicadoListView.as_view(), name="lista"),
    path("nuevo/", views.ComunicadoCreateView.as_view(), name="nuevo"),
    path("<int:pk>/", views.ComunicadoDetailView.as_view(), name="detalle"),
    path("<int:pk>/leido/", views.MarcarLeidoView.as_view(), name="marcar_leido"),
    path("<int:pk>/editar/", views.ComunicadoUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ComunicadoDeleteView.as_view(), name="eliminar"),
    # Aviso prioritario (#118)
    path("aviso/", views.AvisoPrioritarioView.as_view(), name="aviso_prioritario"),
    path("<int:pk>/confirmar-aviso/", views.ConfirmarAvisoView.as_view(), name="confirmar_aviso"),
    path("<int:pk>/lecturas/", views.LecturasComunicadoView.as_view(), name="lecturas"),
]
