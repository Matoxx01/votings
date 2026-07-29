"""
Módulo de rate limiting basado en Django cache.

Provee funciones y un decorador para limitar la tasa de peticiones
por IP + acción, sin dependencias externas (usa LocMemCache).
"""
import time
import logging
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """
    Obtiene la IP real del cliente considerando proxies (Railway/Edge).
    Preferimos HTTP_X_REAL_IP si está presente. En X-Forwarded-For,
    la IP original del cliente siempre es la primera (ips[0]).
    """
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
        if ips:
            return ips[0]
            
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _make_cache_key(ip, action):
    """Genera la clave de caché para un par IP + acción."""
    return f"ratelimit:{action}:{ip}"


def record_attempt(request, action, window_seconds):
    """
    Registra un intento para la IP del request en la acción dada.

    Args:
        request: HttpRequest de Django
        action: Nombre de la acción (ej: 'login_militante')
        window_seconds: Ventana de tiempo en segundos
    """
    try:
        ip = _get_client_ip(request)
        key = _make_cache_key(ip, action)
        now = time.time()

        # Obtener lista de timestamps de intentos anteriores
        attempts = cache.get(key, [])

        # Filtrar solo los intentos dentro de la ventana
        attempts = [t for t in attempts if now - t < window_seconds]

        # Agregar el intento actual
        attempts.append(now)

        # Guardar con TTL igual a la ventana
        cache.set(key, attempts, window_seconds)
    except Exception as e:
        logger.error(f"Error en record_attempt rate limit: {e}")


def is_rate_limited(request, action, max_attempts, window_seconds):
    """
    Verifica si la IP del request excedió el límite de intentos.

    Args:
        request: HttpRequest de Django
        action: Nombre de la acción
        max_attempts: Máximo de intentos permitidos en la ventana
        window_seconds: Ventana de tiempo en segundos

    Returns:
        bool: True si está limitado, False si puede continuar
    """
    try:
        ip = _get_client_ip(request)
        key = _make_cache_key(ip, action)
        now = time.time()

        attempts = cache.get(key, [])

        # Filtrar solo los intentos dentro de la ventana
        valid_attempts = [t for t in attempts if now - t < window_seconds]

        return len(valid_attempts) >= max_attempts
    except Exception as e:
        logger.error(f"Error en is_rate_limited rate limit: {e}")
        return False


def get_wait_seconds(request, action, window_seconds):
    """
    Devuelve cuántos segundos faltan para que expire el bloqueo.

    Args:
        request: HttpRequest de Django
        action: Nombre de la acción
        window_seconds: Ventana de tiempo en segundos

    Returns:
        int: Segundos restantes (0 si no está bloqueado)
    """
    try:
        ip = _get_client_ip(request)
        key = _make_cache_key(ip, action)
        now = time.time()

        attempts = cache.get(key, [])
        if not attempts:
            return 0

        # El intento más antiguo dentro de la ventana determina cuándo se libera
        valid_attempts = [t for t in attempts if now - t < window_seconds]
        if not valid_attempts:
            return 0

        oldest = min(valid_attempts)
        remaining = window_seconds - (now - oldest)
        return max(0, int(remaining))
    except Exception as e:
        logger.error(f"Error en get_wait_seconds rate limit: {e}")
        return 0


def rate_limit_check(request, action, max_attempts, window_seconds):
    """
    Función compuesta: verifica rate limit y retorna info útil.

    Returns:
        tuple: (is_limited: bool, wait_seconds: int)
    """
    limited = is_rate_limited(request, action, max_attempts, window_seconds)
    wait = get_wait_seconds(request, action, window_seconds) if limited else 0
    return limited, wait


def rate_limit_json(action, max_attempts, window_seconds):
    """
    Decorador para vistas que retornan JsonResponse.
    Bloquea con HTTP 429 si se excede el rate limit.

    Args:
        action: Nombre de la acción para el rate limit
        max_attempts: Máximo de intentos permitidos
        window_seconds: Ventana de tiempo en segundos
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            limited, wait = rate_limit_check(
                request, action, max_attempts, window_seconds
            )
            if limited:
                logger.warning(
                    f"Rate limit alcanzado: action={action}, "
                    f"ip={_get_client_ip(request)}, wait={wait}s"
                )
                return JsonResponse(
                    {
                        'success': False,
                        'message': f'Demasiados intentos. Espera {wait} segundos.',
                        'rate_limited': True,
                        'wait_seconds': wait,
                    },
                    status=429,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
