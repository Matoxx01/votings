from django import template
from django.utils import timezone
import pytz

register = template.Library()

@register.filter
def to_santiago_time(value):
    """Convierte cualquier datetime a timezone de Santiago de Chile"""
    if value is None:
        return None
    
    # Si ya tiene timezone, convertirlo a Santiago
    santiago_tz = pytz.timezone('America/Santiago')
    if timezone.is_aware(value):
        return value.astimezone(santiago_tz)
    else:
        # Si no tiene timezone, asumimos UTC y convertimos
        value = timezone.make_aware(value, timezone.utc)
        return value.astimezone(santiago_tz)

@register.simple_tag
def current_santiago_time():
    """Retorna la hora actual en timezone de Santiago"""
    santiago_tz = pytz.timezone('America/Santiago')
    return timezone.now().astimezone(santiago_tz)
