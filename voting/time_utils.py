"""
Utilidades para obtener tiempo real desde internet usando NTP
"""
import ntplib
from datetime import datetime
import pytz
from django.utils import timezone

# Caché de la última hora NTP obtenida
_last_santiago_time = None
_last_fetch_timestamp = None
CACHE_SECONDS = 300  # Cachear durante 5 minutos


def get_ntp_santiago_time():
    """
    Obtiene la hora actual desde un servidor NTP y la convierte a Santiago de Chile
    Returns: datetime aware en timezone America/Santiago
    """
    try:
        # Obtener hora UTC desde servidor NTP
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', version=3, timeout=5)
        utc_time = datetime.fromtimestamp(response.tx_time, tz=pytz.utc)
        
        # Convertir a timezone de Santiago de Chile
        santiago_tz = pytz.timezone('America/Santiago')
        santiago_time = utc_time.astimezone(santiago_tz)
        
        return santiago_time
    except Exception:
        return None


def get_real_now():
    """
    Obtiene la hora actual real de Santiago de Chile desde internet (usando NTP)
    Cachea el resultado durante 5 minutos para evitar sobrecarga
    Returns: datetime aware en timezone America/Santiago
    """
    global _last_santiago_time, _last_fetch_timestamp
    
    import time
    current_timestamp = time.time()
    
    # Si no hay caché o pasaron más de 5 minutos, obtener nueva hora
    if _last_santiago_time is None or _last_fetch_timestamp is None or (current_timestamp - _last_fetch_timestamp) > CACHE_SECONDS:
        # Intentar obtener hora desde NTP
        santiago_time = get_ntp_santiago_time()
        
        if santiago_time:
            _last_santiago_time = santiago_time
            _last_fetch_timestamp = current_timestamp
            return santiago_time
        else:
            # Fallback: si falla NTP, usar hora del sistema
            print("WARNING: No se pudo obtener hora NTP, usando hora del sistema")
            if _last_santiago_time is None:
                # Primera vez y falló, usar sistema como última opción
                santiago_tz = pytz.timezone('America/Santiago')
                return timezone.now().astimezone(santiago_tz)
            else:
                # Si teníamos hora NTP previa, estimar tiempo transcurrido
                time_passed = current_timestamp - _last_fetch_timestamp
                estimated_time = _last_santiago_time + timezone.timedelta(seconds=time_passed)
                return estimated_time
    else:
        # Usar caché y estimar el tiempo transcurrido
        time_passed = current_timestamp - _last_fetch_timestamp
        estimated_time = _last_santiago_time + timezone.timedelta(seconds=time_passed)
        return estimated_time
