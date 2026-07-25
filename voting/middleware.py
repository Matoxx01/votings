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
