"""
Límite de intentos de inicio de sesión (Issue #52, NTI-09 y RNF02).

Regla: 5 intentos fallidos en 15 minutos, con el mismo correo o desde la misma
dirección, bloquean el ingreso. El bloqueo termina solo: cuando los intentos
salen de la ventana, se puede volver a entrar. Los intentos durante el bloqueo
no se registran, así que no lo alargan.

Se cuentan también los correos sin cuenta y el mensaje es siempre el mismo:
así el bloqueo no revela qué correos están registrados.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import IntentoFallido

MAX_INTENTOS = 5
VENTANA = timedelta(minutes=15)
MENSAJE_BLOQUEO = "Demasiados intentos. Espera hasta 15 minutos o usa «¿Olvidaste tu contraseña?» para crear una nueva."


def normalizar_correo(correo):
    """Sin espacios y en minúsculas: variar las mayúsculas no evita el límite."""
    return (correo or "").strip().lower()[:254]


def direccion_cliente(request):
    """
    Dirección IP de quien hace la petición.

    Detrás de un proxy, REMOTE_ADDR es la del proxy y todas las visitas parecerían
    venir del mismo lugar. Con CUENTAS_PROXIES_CONFIABLES = n (cantidad de proxies
    propios) se toma de X-Forwarded-For la dirección n contando desde la derecha.
    Sin esa configuración la cabecera se ignora: el visitante puede falsificarla.
    """
    if request is None:
        return ""
    proxies = int(getattr(settings, "CUENTAS_PROXIES_CONFIABLES", 0))  # int(): puede venir de una variable de entorno
    if proxies > 0:
        cadena = [parte.strip() for parte in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if parte.strip()]
        if len(cadena) >= proxies:
            return cadena[-proxies][:45]
    return request.META.get("REMOTE_ADDR", "")[:45]


def esta_bloqueado(correo, direccion):
    """True si el correo o la dirección llegaron al límite dentro de la ventana."""
    recientes = IntentoFallido.objects.filter(creado__gt=timezone.now() - VENTANA)
    if correo and recientes.filter(correo=correo).count() >= MAX_INTENTOS:
        return True
    # Sin dirección conocida no se cuenta por dirección: juntaría a personas distintas.
    return bool(direccion) and recientes.filter(direccion=direccion).count() >= MAX_INTENTOS


def borrar_antiguos():
    """Correo e IP son datos personales: fuera de la ventana ya no sirven y no se guardan."""
    IntentoFallido.objects.filter(creado__lte=timezone.now() - VENTANA).delete()


def registrar_fallo(correo, direccion):
    """Guarda el intento."""
    borrar_antiguos()
    IntentoFallido.objects.create(correo=correo, direccion=direccion)


def limpiar_correo(correo):
    """
    Borra los intentos de un correo, al ingresar bien o al crear una contraseña nueva.
    Solo los de ese correo: si se borraran los de la dirección, un atacante podría
    reiniciar el contador ingresando con su propia cuenta entre intentos contra otras.
    Por eso, si la dirección llegó al límite con otros correos, sigue bloqueada.
    """
    borrar_antiguos()
    IntentoFallido.objects.filter(correo=normalizar_correo(correo)).delete()
