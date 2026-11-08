"""
Modelo de auditoría: quién hizo qué, en qué condominio, cuándo y con qué valores (Ley 21.719, Issue #27).

Un registro es inmutable: una vez guardado no se edita ni se borra. Así, lo que quedó
registrado es una prueba fiable aunque después cambie el usuario o el objeto.
"""
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class RegistroInmutable(Exception):
    """Se intentó editar o borrar un registro de auditoría que ya existe."""


class RegistroAuditoriaQuerySet(models.QuerySet):
    """
    Bloquea update() y delete() en bloque. Sin esto, un queryset podría cambiar o borrar
    registros aunque el modelo no lo permita en save() o delete().
    """

    def update(self, **kwargs):
        raise RegistroInmutable("Los registros de auditoría no se pueden modificar.")

    def delete(self):
        raise RegistroInmutable("Los registros de auditoría no se pueden borrar.")


class RegistroAuditoria(models.Model):
    # El condominio y el usuario se guardan como número y texto, sin clave foránea.
    # Así el registro sigue existiendo aunque se borre la cuenta o el condominio, y
    # `usuario_nombre` conserva cómo se llamaba la persona en ese momento.
    # Al no ser FK, CondominioQuerysetMixin no sirve tal cual: la vista debe filtrar con
    # `condominio_id=request.condominio.pk` (ver design.md).
    condominio_id = models.PositiveBigIntegerField()
    usuario_id = models.PositiveBigIntegerField(null=True, blank=True)
    usuario_nombre = models.CharField(max_length=150)
    accion = models.CharField(max_length=40)
    objeto_tipo = models.CharField(max_length=60)
    objeto_id = models.CharField(max_length=60)
    # Solo los campos que cambian. JSON nulo cuando el evento no tiene valores anteriores o nuevos.
    antes = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    despues = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    creado = models.DateTimeField(auto_now_add=True)

    objects = RegistroAuditoriaQuerySet.as_manager()

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ["-creado", "-id"]
        indexes = [
            # Para la vista de filtros del PR siguiente: por condominio y fecha, y por usuario.
            models.Index(fields=["condominio_id", "creado"], name="aud_condo_creado_idx"),
            models.Index(fields=["usuario_id"], name="aud_usuario_idx"),
        ]

    def save(self, *args, **kwargs):
        # Si la fila ya existe, es una edición: se rechaza. Solo se permite insertar.
        # También se rechaza un objeto nuevo con id puesto a mano: Django haría un UPDATE
        # sobre la fila con ese id y reemplazaría el registro original.
        if not self._state.adding or self.pk is not None:
            raise RegistroInmutable("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RegistroInmutable("Los registros de auditoría no se pueden borrar.")

    def __str__(self):
        return f"{self.creado:%Y-%m-%d %H:%M} · {self.usuario_nombre} · {self.accion} · {self.objeto_tipo} {self.objeto_id}"
