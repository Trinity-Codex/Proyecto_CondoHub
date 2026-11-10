"""
Modelo de cartera: el acceso de «administrador general» (Issue #54, RF20).

Un administrador general es una persona a la que el superusuario le asigna uno o más
condominios para CONSULTAR su cartera (emitido, recaudado y morosidad). No es un rol de la
membresía (`condominios.Membresia`): no le da un condominio activo ni permisos dentro de
ningún condominio, solo la página `/cartera/`. Ver `permisos.py` y `consolidado.py`.
"""
from django.conf import settings
from django.db import models


class AsignacionCartera(models.Model):
    """Un condominio que una persona puede consultar en su cartera. Una fila por par persona-condominio."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaciones_cartera",
        verbose_name="administrador general",
    )
    condominio = models.ForeignKey(
        "condominios.Condominio", on_delete=models.CASCADE, related_name="asignaciones_cartera"
    )
    asignada_el = models.DateTimeField("asignada el", auto_now_add=True)

    class Meta:
        verbose_name = "acceso de administrador general"
        verbose_name_plural = "accesos de administrador general"
        ordering = ["usuario__email", "condominio__nombre"]
        constraints = [
            models.UniqueConstraint(fields=["usuario", "condominio"], name="uq_asignacion_cartera"),
        ]

    def __str__(self):
        return f"{self.usuario.email} · {self.condominio}"
