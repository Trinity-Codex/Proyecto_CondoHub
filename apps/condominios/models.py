"""
Modelos de condominios, edificios, unidades, residentes y roles (RF01).

Basado en el modelo de datos del Informe 2 (tablas edificio, unidad, residente
y administrador), con dos cambios para que CondoHub sirva a MUCHOS condominios:

  - Se agrega Condominio, que agrupa todo: cada edificio, comunicado, espacio
    común, etc. pertenece a un condominio. Así los datos de una comunidad
    nunca se mezclan con los de otra.
  - "residente" y "administrador" ya no son tablas con nombre/RUT/correo:
    esos datos están en el Usuario (apps/cuentas). Aquí se guarda qué ROL
    tiene cada usuario en cada condominio (Membresia) y en qué unidad vive
    (Residente).

Jerarquía:  Condominio -> Edificio -> Unidad <- Residente -> Usuario
                 |
                 +-> Membresia (rol del usuario en ese condominio)
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Condominio(models.Model):
    """Comunidad administrada en la plataforma (ej. "Condominio Vista Verde")."""

    nombre = models.CharField(max_length=120)
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def suma_alicuotas(self):
        """
        Suma de las alícuotas de todas sus unidades. Debería ser 1 (100 %)
        para que el prorrateo de los gastos comunes reparta el total exacto.
        """
        total = Unidad.objects.filter(edificio__condominio=self).aggregate(s=models.Sum("alicuota"))["s"]
        return total or Decimal("0")


class Edificio(models.Model):
    """Torre o bloque dentro de un condominio."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="edificios")
    nombre = models.CharField(max_length=80)
    direccion = models.CharField("dirección", max_length=200, blank=True)

    class Meta:
        ordering = ["condominio", "nombre"]
        constraints = [
            # No puede haber dos edificios con el mismo nombre en un condominio.
            models.UniqueConstraint(fields=["condominio", "nombre"], name="uq_edificio_nombre"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.condominio})"

    def motivos_para_no_eliminar(self):
        """
        Razones que impiden borrar el edificio. Borrarlo eliminaría EN CASCADA
        sus unidades (con residentes y reservas) y sus comunicados, así que
        primero hay que vaciarlo. Lista vacía = se puede eliminar.
        """
        motivos = []
        if self.unidades.exists():
            motivos.append("tiene unidades registradas (elimínalas primero)")
        if self.comunicados.exists():
            motivos.append("tiene comunicados dirigidos a él")
        return motivos


class Unidad(models.Model):
    """Departamento, casa, local, estacionamiento o bodega."""

    class Tipo(models.TextChoices):
        DEPARTAMENTO = "DEPARTAMENTO", "Departamento"
        CASA = "CASA", "Casa"
        LOCAL = "LOCAL", "Local comercial"
        ESTACIONAMIENTO = "ESTACIONAMIENTO", "Estacionamiento"
        BODEGA = "BODEGA", "Bodega"

    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name="unidades")
    numero = models.CharField("número", max_length=10)
    piso = models.SmallIntegerField(default=1)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.DEPARTAMENTO)
    # Alícuota (prorrateo): parte de los gastos comunes que paga la unidad,
    # como fracción del total. Ej.: 0.012500 = 1,25 %. La Ley 21.442 establece
    # que se paga en proporción al derecho sobre los bienes comunes.
    alicuota = models.DecimalField(
        "alícuota",
        max_digits=7,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
        help_text="Fracción del total (ej. 0.012500 = 1,25 %).",
    )

    class Meta:
        ordering = ["edificio", "piso", "numero"]
        verbose_name_plural = "unidades"
        constraints = [
            models.UniqueConstraint(fields=["edificio", "numero"], name="uq_unidad_numero"),
        ]

    def __str__(self):
        return f"{self.edificio.nombre} - {self.numero}"

    @property
    def condominio(self):
        return self.edificio.condominio

    def motivos_para_no_eliminar(self):
        """
        Razones que impiden borrar la unidad (se perderían residentes, reservas
        o su historial de cobros). Los cobros además los protege la base de
        datos (on_delete=RESTRICT en DetalleGastoComun): sin este aviso, el
        intento terminaría en un error en vez de un mensaje claro.
        """
        motivos = []
        if self.residentes.filter(activo=True).exists():
            motivos.append("tiene residentes activos (dalos de baja primero)")
        if self.reservas.exists():
            motivos.append("tiene reservas registradas")
        if self.cobros.exists():
            motivos.append("tiene cobros de gastos comunes (su historial de deudas y pagos)")
        return motivos


class Membresia(models.Model):
    """
    Rol de un usuario dentro de un condominio. Define qué puede hacer en el sitio.

    Una persona puede tener varios roles en el mismo condominio (por ejemplo,
    residente y miembro del comité) y roles distintos en otros condominios.
    """

    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        COMITE = "COMITE", "Comité de administración"
        RESIDENTE = "RESIDENTE", "Residente"
        CONSERJE = "CONSERJE", "Conserje"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membresias")
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="membresias")
    rol = models.CharField(max_length=20, choices=Rol.choices)
    activo = models.BooleanField(default=True)
    desde = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "membresía"
        verbose_name_plural = "membresías"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "condominio", "rol"], name="uq_membresia_rol"),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.get_rol_display()} en {self.condominio}"


class Residente(models.Model):
    """Persona que vive (o es dueña) de una unidad. Tabla "residente" del Informe 2."""

    class Tipo(models.TextChoices):
        PROPIETARIO = "PROPIETARIO", "Propietario"
        ARRENDATARIO = "ARRENDATARIO", "Arrendatario"
        FAMILIAR = "FAMILIAR", "Familiar / otro ocupante"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="residencias")
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="residentes")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PROPIETARIO)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "unidad"], name="uq_residente_unidad"),
        ]

    def __str__(self):
        return f"{self.usuario} ({self.get_tipo_display()}) - {self.unidad}"

    def save(self, *args, **kwargs):
        """
        Al registrar a alguien como residente activo de una unidad, se le da
        también el rol RESIDENTE en ese condominio (o se reactiva si estaba
        dado de baja), para que pueda entrar al sitio con esos permisos.
        """
        super().save(*args, **kwargs)
        if self.activo:
            membresia, _ = Membresia.objects.get_or_create(
                usuario=self.usuario,
                condominio=self.unidad.edificio.condominio,
                rol=Membresia.Rol.RESIDENTE,
            )
            if not membresia.activo:
                membresia.activo = True
                membresia.save(update_fields=["activo"])

    def dar_de_baja(self):
        """
        Deja de ser residente de la unidad. No se borra (queda el historial).
        Si ya no vive en ninguna otra unidad del condominio, pierde también el
        rol RESIDENTE allí (sus otros roles, como comité, se mantienen).
        """
        self.activo = False
        self.save(update_fields=["activo"])
        condominio = self.unidad.edificio.condominio
        sigue_viviendo = Residente.objects.filter(
            usuario=self.usuario, unidad__edificio__condominio=condominio, activo=True
        ).exists()
        if not sigue_viviendo:
            Membresia.objects.filter(
                usuario=self.usuario, condominio=condominio, rol=Membresia.Rol.RESIDENTE
            ).update(activo=False)
