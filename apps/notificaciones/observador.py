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
    NotificadorEnSitio (crea notificaciones en la campana del sitio) y
    NotificadorCorreo (envía un correo, Issue #14).
  - Los observadores se SUSCRIBEN al sujeto (en apps.py, al iniciar Django).

Para agregar un canal nuevo basta con crear otra clase Observador y
suscribirla: no se toca el código de comunicados ni de incidentes. Así se
agregó el correo (Issue #14): NotificadorCorreo + una línea por sujeto en apps.py.

    Comunicado ──notificar(evento)──> [NotificadorEnSitio, NotificadorCorreo, ...]
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


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


class NotificadorCorreo(Observador):
    """
    Observador concreto (Issue #14): envía un correo a cada destinatario que
    acepta recibirlos (Usuario.recibir_correos, se cambia en "Mi perfil").

    En desarrollo los correos se imprimen en la consola del servidor
    (EMAIL_BACKEND de consola en settings.py); en las pruebas quedan en
    django.core.mail.outbox.
    """

    def actualizar(self, evento: Evento):
        # Sin duplicados (por pk) y solo quien quiere correos y tiene la cuenta activa.
        usuarios = {
            usuario.pk: usuario
            for usuario in evento.destinatarios
            if usuario.email and usuario.is_active and usuario.recibir_correos
        }
        if not usuarios:
            return
        # on_commit: el correo sale DESPUÉS de que los datos se guardan de verdad.
        # Emitir gastos o registrar un pago ocurre en una transacción; si al final
        # falla y se deshace, no queremos haber avisado de algo que no pasó.
        # (Fuera de una transacción, on_commit ejecuta la función de inmediato.)
        transaction.on_commit(lambda: self.enviar(evento, list(usuarios.values())))

    def enviar(self, evento, usuarios):
        """Un correo por persona (con su nombre), todos por la misma conexión al servidor de correo."""
        enlace = f"{settings.SITIO_URL}{evento.url}" if evento.url else settings.SITIO_URL
        try:
            with get_connection() as conexion:
                for usuario in usuarios:
                    cuerpo = render_to_string(
                        "notificaciones/correo_aviso.txt",
                        {
                            "usuario": usuario,
                            "evento": evento,
                            "enlace": enlace,
                            "perfil": f"{settings.SITIO_URL}{reverse('cuentas:perfil')}",
                        },
                    )
                    send_mail(
                        subject=f"[CondoHub] {evento.titulo}",
                        message=cuerpo,
                        from_email=None,  # usa DEFAULT_FROM_EMAIL
                        recipient_list=[usuario.email],
                        connection=conexion,
                    )
        except Exception:
            # Si el servidor de correo falla, lo demás sigue funcionando: el
            # comunicado ya se publicó y la campana ya avisó. Solo queda en el log.
            logger.exception("No se pudieron enviar los avisos por correo de «%s».", evento.titulo)
