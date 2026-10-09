"""Modelo de proveedores: empresas o personas que prestan servicios al condominio."""
from django.db import models

from apps.cuentas.validadores import normalizar_rut, validar_rut


class Proveedor(models.Model):
    # REGLA MULTI-CONDOMINIO: cada proveedor pertenece a un solo condominio.
    condominio = models.ForeignKey("condominios.Condominio", on_delete=models.CASCADE, related_name="proveedores")
    # El RUT se valida (formato y dígito verificador) y se guarda normalizado: "12345678-5".
    rut = models.CharField("RUT", max_length=12, validators=[validar_rut])
    razon_social = models.CharField("razón social", max_length=150)
    rubro = models.CharField(max_length=80, help_text="Ej.: ascensores, jardinería, aseo.")
    contacto = models.CharField("persona de contacto", max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    correo = models.EmailField("correo electrónico", blank=True)
    # En vez de borrar un proveedor se desactiva: así no se pierde su historial (ej. egresos).
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["razon_social"]
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        constraints = [
            # Última barrera en la base de datos: no puede haber dos veces el mismo RUT en un condominio.
            models.UniqueConstraint(fields=["condominio", "rut"], name="proveedor_rut_unico_por_condominio"),
        ]

    def save(self, *args, **kwargs):
        # Garantiza que el RUT siempre quede normalizado, venga de donde venga.
        self.rut = normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.razon_social} ({self.rut})"