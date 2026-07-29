from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class SecurityBlockMiddleware(MiddlewareMixin):
    """
    Middleware que bloquea requests de IPs que han sido 
    bloqueadas permanentemente por un administrador.
    """

    def process_request(self, request):
        from voting.security import SecurityService, _get_client_ip
        
        ip = _get_client_ip(request)
        
        if SecurityService.is_ip_blocked(ip):
            return HttpResponseForbidden(
                '<h1>Acceso Denegado</h1>'
                '<p>Tu direccion IP ha sido bloqueada por el administrador del sistema.</p>',
                content_type='text/html'
            )
        
        return None


class UserTimezoneMiddleware(MiddlewareMixin):
    """
    Middleware que activa la zona horaria del usuario según la cookie `django_timezone`
    enviada por el navegador. Si no existe la cookie, se desactiva y usa la predeterminada.
    """

    def process_request(self, request):
        import zoneinfo
        import pytz
        from django.utils import timezone

        tzname = request.COOKIES.get('django_timezone')
        if tzname:
            try:
                try:
                    tz = zoneinfo.ZoneInfo(tzname)
                except Exception:
                    tz = pytz.timezone(tzname)
                timezone.activate(tz)
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()
        return None

