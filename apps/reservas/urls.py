"""Rutas de reservas (prefijo /reservas/)."""
from django.urls import path

from . import views

app_name = "reservas"

urlpatterns = [
    path("", views.EspacioListView.as_view(), name="espacios"),
    path("espacios/nuevo/", views.EspacioCreateView.as_view(), name="espacio_nuevo"),
    path("espacios/<int:pk>/", views.EspacioDetailView.as_view(), name="espacio_detalle"),
    path("espacios/<int:pk>/editar/", views.EspacioUpdateView.as_view(), name="espacio_editar"),
    path("nueva/", views.ReservaCreateView.as_view(), name="nueva"),
    path("mis-reservas/", views.MisReservasView.as_view(), name="mis_reservas"),
    path("todas/", views.ReservaListView.as_view(), name="todas"),
    path("<int:pk>/cancelar/", views.cancelar_reserva, name="cancelar"),
]
