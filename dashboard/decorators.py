from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def maintainer_login_required(view_func):
    """Decorador para requerir login de maintainer"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('maintainer_id'):
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect('dashboard:login')
        return view_func(request, *args, **kwargs)
    return wrapper
