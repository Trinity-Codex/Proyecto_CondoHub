from django import template

from apps.core.formato import formatear_monto

register = template.Library()
register.filter("miles", formatear_monto)
