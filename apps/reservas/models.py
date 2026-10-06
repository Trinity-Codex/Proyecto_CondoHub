"""
Reservas de espacios comunes (RF05 y RF06).

RF05: consultar la disponibilidad de un espacio y reservarlo (fecha y horario).
RF06: impedir que un espacio se reserve dos veces en horarios que se TOPAN.

Mejora respecto del script SQL del Informe 2: allí un índice único solo
impedía dos reservas con la MISMA hora de inicio. Aquí se detecta cualquier
superposición (ej. 10:00-12:00 contra 11:00-13:00). Dos rangos [A, B) y
[C, D) se topan si  A < D  y  C < B.
"""
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class EspacioComun(models.Model):
    """Quincho, salón de eventos, gimnasio, etc."""

    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="espacios")
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    capacidad = models.PositiveIntegerField(help_text="Número máximo de personas.")
    # Tarifa por reserva en pesos chilenos (0 = gratis). Su cobro en los gastos
    # comunes es una feature del backlog.
    tarifa = models.PositiveIntegerField(default=0, help_text="Pesos chilenos por reserva (0 = gratis).")
    hora_apertura = models.TimeField(default="09:00")
    hora_cierre = models.TimeField(default="22:00")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "espacio común"
        verbose_name_plural = "espacios comunes"
        ordering = ["condominio", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["condominio", "nombre"], name="uq_espacio_nombre"),
        ]

    def __str__(self):
        return self.nombre

    def reservas_que_topan(self, fecha, hora_inicio, hora_fin, excluir_pk=None):
        """Reservas CONFIRMADAS de este espacio que se superponen con el horario indicado."""
        reservas = self.reservas.filter(
            fecha=fecha,
            estado=Reserva.Estado.CONFIRMADA,
            hora_inicio__lt=hora_fin,  # A < D
            hora_fin__gt=hora_inicio,  # C < B
        )
        if excluir_pk:
            reservas = reservas.exclude(pk=excluir_pk)
        return reservas


class Reserva(models.Model):
    class Estado(models.TextChoices):
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"

    espacio = models.ForeignKey(EspacioComun, on_delete=models.CASCADE, related_name="reservas")
    unidad = models.ForeignKey("condominios.Unidad", on_delete=models.CASCADE, related_name="reservas")
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservas")
    fecha = models.DateField()
    hora_inicio = models.TimeField("hora de inicio")
    hora_fin = models.TimeField("hora de término")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.CONFIRMADA)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora_inicio"]
        indexes = [models.Index(fields=["espacio", "fecha"])]
        constraints = [
            # Igual que el CHECK del script SQL del Informe 2.
            models.CheckConstraint(
                condition=models.Q(hora_fin__gt=models.F("hora_inicio")), name="ck_reserva_horario"
            ),
        ]

    def __str__(self):
        return f"{self.espacio} {self.fecha:%d-%m-%Y} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"

    def clean(self):
        """
        Reglas de negocio. Django llama a clean() al validar un formulario
        (form.is_valid()). Cada error se asocia al campo que lo provocó.
        """
        if not (self.fecha and self.hora_inicio and self.hora_fin and self.espacio_id):
            return  # faltan datos: los errores de "campo obligatorio" los da el formulario
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})
        if self.fecha < date.today():
            raise ValidationError({"fecha": "No se puede reservar en una fecha pasada."})
        espacio = self.espacio
        if self.hora_inicio < espacio.hora_apertura or self.hora_fin > espacio.hora_cierre:
            raise ValidationError(
                f"{espacio} se puede reservar entre las {espacio.hora_apertura:%H:%M} "
                f"y las {espacio.hora_cierre:%H:%M}."
            )
        if self.unidad_id and self.unidad.edificio.condominio_id != espacio.condominio_id:
            raise ValidationError({"unidad": "La unidad no pertenece al condominio del espacio."})
        if espacio.reservas_que_topan(self.fecha, self.hora_inicio, self.hora_fin, excluir_pk=self.pk).exists():
            raise ValidationError("El espacio ya está reservado en ese horario (RF06). Elige otro horario.")

    @transaction.atomic
    def confirmar(self):
        """
        Guarda la reserva evitando que dos personas reserven el mismo horario
        al mismo tiempo: select_for_update() BLOQUEA la fila del espacio hasta
        que termina la transacción, así la segunda petición espera y luego ve
        la primera reserva al validar.
        """
        EspacioComun.objects.select_for_update().get(pk=self.espacio_id)
        self.full_clean()
        self.save()

    def cancelar(self):
        self.estado = self.Estado.CANCELADA
        self.save(update_fields=["estado"])
