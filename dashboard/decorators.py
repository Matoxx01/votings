from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from voting.models import Maintainer


def maintainer_login_required(view_func):
    """Decorador para requerir login de maintainer"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('maintainer_id'):
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect('dashboard:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorador para requerir rol de administrador"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('maintainer_id'):
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect('dashboard:login')
        
        try:
            maintainer = Maintainer.objects.get(id=request.session.get('maintainer_id'))
            # Verificar si el rol contiene 'Admin' o si es el rol con id específico
            if maintainer.id_role.name.lower() not in ['admin', 'administrador']:
                messages.error(request, "No tienes permisos para acceder a esta página.")
                return redirect('dashboard:dashboard')
        except Maintainer.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
            return redirect('dashboard:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def no_auditor(view_func):
    """Decorador para excluir auditores de ciertas vistas"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('maintainer_id'):
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect('dashboard:login')
        
        try:
            maintainer = Maintainer.objects.get(id=request.session.get('maintainer_id'))
            if maintainer.id_role.name.lower() == 'auditor':
                messages.error(request, "No tienes permisos para acceder a esta página.")
                return redirect('dashboard:dashboard')
        except Maintainer.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
            return redirect('dashboard:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper

