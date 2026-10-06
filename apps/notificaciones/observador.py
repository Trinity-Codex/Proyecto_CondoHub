"""
Patrón de diseño OBSERVER (Informe 2, sección 5.3).

Problema: cuando se publica un comunicado o cambia el estado de un incidente,
los residentes deben enterarse (RF10). Si el código de comunicados llamara
directamente a "crear notificación", "enviar correo", "enviar push"... cada
canal nuevo obligaría a modificar comunicados, incidentes, etc.

Solución Observer:
  - SUJETO (Subject): el que "avisa" que pasó algo. Aquí: Comunicado e
    Incidente (heredan de Sujeto). No sabe quién lo escucha.
  - OBSERVADOR (Observer): el que reacciona al aviso. Aquí:
    NotificadorEnSitio (crea notificaciones en la campana del sitio).
  - Los observadores se SUSCRIBEN al sujeto (en apps.py, al iniciar Django).

Para agregar un canal nuevo (por ejemplo correo electrónico, issue del
backlog) basta con crear otra clase Observador y suscribirla: no se toca el
código de comunicados ni de incidentes.

    Comunicado ──notificar(evento)──> [NotificadorEnSitio, NotificadorCorreo, ...]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Evento:
    """Lo que el sujeto comunica a sus observadores."""

    condominio: object          # Condominio donde ocurrió
    titulo: str                 # texto corto ("Nuevo comunicado")
    mensaje: str                # detalle
    destinatarios: list = field(default_factory=list)  # usuarios a avisar
    url: str = ""               # enlace para ver el detalle en el sitio


class Observador(ABC):
    """Interfaz que deben cumplir todos los observadores (IObservador del Informe 2)."""

    @abstractmethod
    def actualizar(self, evento: Evento):
        """Se llama cada vez que un sujeto al que está suscrito notifica algo."""


class Sujeto:
    """
    Clase base de los sujetos (ISujeto del Informe 2).

    La lista de observadores es POR CLASE: todos los comunicados comparten los
    mismos observadores. Cada subclase tiene su propia lista (ver suscribir()).
    """

    _observadores = None

    @classmethod
    def suscribir(cls, observador: Observador):
        # Se crea la lista la primera vez, en la propia subclase (no en Sujeto),
        # para que Comunicado e Incidente no compartan observadores por error.
        if "_observadores" not in cls.__dict__ or cls._observadores is None:
            cls._observadores = []
        if observador not in cls._observadores:
            cls._observadores.append(observador)

    @classmethod
    def desuscribir(cls, observador: Observador):
        if cls.__dict__.get("_observadores"):
            cls._observadores.remove(observador)

    def notificar(self, evento: Evento):
        """Avisa del evento a todos los observadores suscritos a esta clase."""
        for observador in type(self).__dict__.get("_observadores") or []:
            observador.actualizar(evento)


class NotificadorEnSitio(Observador):
    """Observador concreto: guarda una notificación para cada destinatario (campana del menú)."""

    def actualizar(self, evento: Evento):
        from .models import Notificacion  # import aquí para evitar import circular

        Notificacion.objects.bulk_create(
            [
                Notificacion(
                    usuario=usuario,
                    condominio=evento.condominio,
                    titulo=evento.titulo,
                    mensaje=evento.mensaje,
                    url=evento.url,
                )
                for usuario in set(evento.destinatarios)  # set(): sin duplicados
            ]
        )
