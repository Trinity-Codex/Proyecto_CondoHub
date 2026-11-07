"""
Modelo de usuario de CondoHub.

Se usa un usuario PROPIO (en vez del que trae Django) por dos motivos:
  1. Iniciar sesión con el correo electrónico en vez de un "nombre de usuario".
  2. Guardar datos propios de Chile, como el RUT.
Django recomienda definirlo al comenzar el proyecto: cambiarlo después de la
primera migración es muy difícil. Se activa en settings.py con AUTH_USER_MODEL.

Un mismo usuario puede tener distintos ROLES en distintos condominios
(por ejemplo, administrador de uno y residente de otro). Los roles NO están
aquí, sino en condominios.Membresia.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from .validadores import normalizar_rut, validar_rut


class UsuarioManager(BaseUserManager):
    """
    "Manager": la clase que crea usuarios (Usuario.objects.create_user(...)).
    Hay que escribirlo porque el de Django exige un "username" y aquí no existe.
    """

    use_in_migrations = True

    def _crear(self, email, password, **campos):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email)
        usuario = self.model(email=email, **campos)
        usuario.set_password(password)  # guarda la clave cifrada (nunca en texto plano)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._crear(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        """Superusuario = administrador de TODA la plataforma (entra al /admin/ de Django)."""
        campos["is_staff"] = True
        campos["is_superuser"] = True
        return self._crear(email, password, **campos)


class Usuario(AbstractUser):
    """Persona que usa CondoHub: administrador, miembro del comité, residente o conserje."""

    username = None  # se elimina el "nombre de usuario": se inicia sesión con el correo
    email = models.EmailField("correo electrónico", unique=True)
    rut = models.CharField("RUT", max_length=12, blank=True, validators=[validar_rut])
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    # Preferencia para los avisos por correo (Issue #14, patrón Observer). Cada
    # persona la cambia en "Mi perfil"; la campana del sitio se muestra siempre.
    recibir_correos = models.BooleanField(
        "recibir avisos por correo",
        default=True,
        help_text="Comunicados, incidentes, gastos comunes emitidos y pagos registrados.",
    )

    USERNAME_FIELD = "email"                     # campo con el que se inicia sesión
    REQUIRED_FIELDS = ["first_name", "last_name"]  # se piden al crear un superusuario

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["first_name", "last_name"]

    def save(self, *args, **kwargs):
        # El RUT se guarda siempre con el mismo formato (sin puntos, K mayúscula).
        if self.rut:
            self.rut = normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email


class IntentoFallido(models.Model):
    """
    Un inicio de sesión fallido (Issue #52). Se guarda en la base de datos porque
    la caché por defecto de Django es por proceso: con varios procesos en
    producción, cada uno contaría por separado. Las reglas están en limite_intentos.py.
    """

    correo = models.CharField(max_length=254)  # normalizado; puede no tener cuenta
    direccion = models.CharField("dirección IP", max_length=45, blank=True)
    creado = models.DateTimeField(default=timezone.now)  # sin auto_now_add: las pruebas simulan el tiempo

    class Meta:
        verbose_name = "intento fallido"
        verbose_name_plural = "intentos fallidos"
        indexes = [
            models.Index(fields=["correo", "creado"], name="ix_intento_correo"),
            models.Index(fields=["direccion", "creado"], name="ix_intento_direccion"),
            models.Index(fields=["creado"], name="ix_intento_creado"),  # para borrar los antiguos sin recorrer la tabla
        ]

    def __str__(self):
        return f"{self.correo} desde {self.direccion} ({self.creado:%d-%m-%Y %H:%M})"
