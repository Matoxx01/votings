from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from pathlib import Path
import io
from voting.models import Voting, Subject, UserData, Count, VotingRecord, Region, Militante, MilitanteRegistrationToken, MilitantePasswordResetToken
from voting.forms import VoterRegistrationForm, MilitanteRegistrationForm, MilitanteLoginForm, MilitantePasswordResetRequestForm, MilitantePasswordResetForm
from voting.services import EmailService
from voting.time_utils import get_real_now


def favicon(request):
    """Sirve el favicon.svg"""
    favicon_path = settings.BASE_DIR / 'favicon.svg'
    if favicon_path.exists():
        with open(favicon_path, 'rb') as f:
            return FileResponse(f, content_type='image/svg+xml')
    return HttpResponse(status=404)


def serve_media(request, path):
    """Sirve archivos media"""
    media_path = settings.MEDIA_ROOT / path
    
    # Verificar que la ruta esté dentro de MEDIA_ROOT (seguridad)
    try:
        media_path.resolve().relative_to(settings.MEDIA_ROOT.resolve())
    except ValueError:
        return HttpResponse(status=403)
    
    if media_path.exists() and media_path.is_file():
        # Determinar el tipo MIME
        content_type = 'application/octet-stream'
        if path.endswith('.jpeg') or path.endswith('.jpg'):
            content_type = 'image/jpeg'
        elif path.endswith('.png'):
            content_type = 'image/png'
        elif path.endswith('.webp'):
            content_type = 'image/webp'
        elif path.endswith('.gif'):
            content_type = 'image/gif'
        
        response = FileResponse(open(media_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{media_path.name}"'
        return response
    
    return HttpResponse(status=404)


def index(request):
    """Vista principal - muestra regiones y votaciones sin región"""
    now = get_real_now()
    
    # Obtener regiones que tienen votaciones abiertas (excepto S/Region id=17)
    regions_with_votings = Region.objects.filter(
        votings__start_date__lte=now,
        votings__finish_date__gte=now
    ).exclude(id=17).distinct().order_by('id')
    
    # Obtener votaciones sin región (S/Region, id=17) abiertas
    votings_without_region = Voting.objects.filter(
        id_region__id=17,
        start_date__lte=now,
        finish_date__gte=now
    ).order_by('-created_at')
    
    # Verificar si hay algún militante logueado
    militante_logged_in = False
    militante_name = None
    for key in request.session.keys():
        if key.startswith('militante_'):
            militante_data = request.session[key]
            militante_logged_in = True
            militante_name = militante_data.get('name', 'Usuario')
            break
    
    context = {
        'regions': regions_with_votings,
        'votings_without_region': votings_without_region,
        'militante_logged_in': militante_logged_in,
        'militante_name': militante_name,
    }
    return render(request, 'voting/index.html', context)


def region_votings(request, region_id):
    """Vista para mostrar votaciones de una región específica"""
    now = get_real_now()
    region = get_object_or_404(Region, id=region_id)
    votings = Voting.objects.filter(
        id_region=region,
        start_date__lte=now,
        finish_date__gte=now
    ).order_by('-created_at')
    
    # Verificar si hay algún militante logueado
    militante_logged_in = False
    militante_name = None
    for key in request.session.keys():
        if key.startswith('militante_'):
            militante_data = request.session[key]
            militante_logged_in = True
            militante_name = militante_data.get('name', 'Usuario')
            break
    
    context = {
        'region': region,
        'votings': votings,
        'militante_logged_in': militante_logged_in,
        'militante_name': militante_name,
    }
    return render(request, 'voting/region_votings.html', context)


def voting_detail(request, voting_id):
    """Vista de detalle de una votación con sus subjects"""
    voting = get_object_or_404(Voting, id=voting_id)
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:index')
    
    # Verificar si el usuario ya está logueado (ahora usa militante)
    session_key = f'militante_{voting_id}'
    if session_key not in request.session:
        # Redirigir a login de militante
        return redirect('voting:militante_login', voting_id=voting_id)
    
    subjects = voting.subjects.all()
    
    context = {
        'voting': voting,
        'subjects': subjects,
    }
    return render(request, 'voting/voting_detail.html', context)


@require_http_methods(["GET", "POST"])
def register(request, voting_id):
    """Vista legacy - redirige a login de militante"""
    return redirect('voting:militante_login', voting_id=voting_id)


@require_http_methods(["GET", "POST"])
def vote(request, subject_id):
    """Vista para confirmar y votar"""
    subject = get_object_or_404(Subject, id=subject_id)
    voting = subject.id_voting
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:voting_detail', voting_id=voting.id)
    
    # Verificar si el usuario está logueado (militante)
    session_key = f'militante_{voting.id}'
    if session_key not in request.session:
        messages.error(request, "Debes iniciar sesión para votar.")
        return redirect('voting:militante_login', voting_id=voting.id)
    
    voter_data = request.session.get(session_key, {})
    
    if request.method == 'POST':
        return process_vote(request, voting, subject, voter_data)
    
    context = {
        'voting': voting,
        'subject': subject,
        'voter_name': voter_data.get('name', ''),
    }
    return render(request, 'voting/vote.html', context)


@transaction.atomic
def process_vote(request, voting, subject, voter_data):
    """
    Procesa el voto del usuario
    """
    rut = voter_data.get('rut')
    mail = voter_data.get('mail')
    name = voter_data.get('name')
    lastname = voter_data.get('lastname', '')
    user_data_id = voter_data.get('user_data_id')
    
    # Obtener el user_data
    try:
        user_data = UserData.objects.get(id=user_data_id)
    except UserData.DoesNotExist:
        messages.error(request, "Error: No se encontraron los datos de registro.")
        return redirect('voting:militante_login', voting_id=voting.id)
    
    # Validar que el usuario no ha votado
    if user_data.has_voted:
        messages.error(request, "Este RUT ya ha votado en esta votación.")
        return redirect('voting:voting_detail', voting_id=voting.id)
    
    try:
        # Registrar el voto de forma ANÓNIMA (sin guardar identidad)
        voting_record = VotingRecord.objects.create(
            id_voting=voting,
            id_subject=subject,
        )
        
        # Incrementar contador
        count, created = Count.objects.get_or_create(id_subject=subject)
        count.number += 1
        count.save()
        
        # Marcar como votado
        user_data.has_voted = True
        user_data.save()
        
        # Limpiar sesión de militante
        session_key = f'militante_{voting.id}'
        if session_key in request.session:
            del request.session[session_key]
            request.session.modified = True
        
        # Enviar correo de confirmación
        try:
            EmailService.send_confirmation_email(
                to_email=mail,
                user_name=f"{name} {lastname}",
                voting_title=voting.title,
            )
        except Exception:
            pass
        
        messages.success(request, "¡Tu voto ha sido registrado correctamente!")
        return redirect('voting:success')
    
    except Exception as e:
        messages.error(request, f"Error al registrar el voto: {str(e)}")
        return redirect('voting:voting_detail', voting_id=voting.id)


def success(request):
    """Vista de éxito después de votar"""
    return render(request, 'voting/success.html')


def voting_statistics(request, voting_id):
    """Vista de estadísticas básicas de una votación (pública)"""
    voting = get_object_or_404(Voting, id=voting_id)

    # Solo permitir acceso si la votación ya finalizó (hora chilena)
    import pytz
    santiago_tz = pytz.timezone('America/Santiago')
    now_chile = get_real_now()
    finish_date_chile = voting.finish_date.astimezone(santiago_tz)
    if finish_date_chile >= now_chile:
        messages.error(request, 'Las estadísticas estarán disponibles una vez que finalice el período de votación.')
        return redirect('voting:voting_detail', voting_id=voting_id)

    subjects = voting.subjects.all()
    
    stats = []
    total_votes = 0
    
    for subject in subjects:
        count = subject.vote_count if hasattr(subject, 'vote_count') else None
        votes = count.number if count else 0
        total_votes += votes
        stats.append({
            'subject': subject,
            'votes': votes,
        })
    
    context = {
        'voting': voting,
        'stats': stats,
        'total_votes': total_votes,
    }
    return render(request, 'voting/statistics.html', context)


# ============================================
# VISTAS DE MILITANTES
# ============================================

@require_http_methods(["GET", "POST"])
def militante_register(request, token):
    """Vista para que un militante complete su registro con token"""
    # Buscar el token
    try:
        token_obj = MilitanteRegistrationToken.objects.get(token=token)
    except MilitanteRegistrationToken.DoesNotExist:
        messages.error(request, "El enlace de registro no es válido.")
        return redirect('voting:index')
    
    # Verificar si el token es válido
    if not token_obj.is_valid():
        messages.error(request, "El enlace de registro ha expirado o ya fue utilizado.")
        return redirect('voting:index')
    
    # Verificar si el RUT ya está registrado
    if Militante.objects.filter(rut=token_obj.rut).exists():
        messages.error(request, "Este RUT ya está registrado en el sistema.")
        token_obj.used = True
        token_obj.save()
        return redirect('voting:index')
    
    if request.method == 'POST':
        form = MilitanteRegistrationForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            password = form.cleaned_data.get('password')
            
            # Verificar que el RUT coincida con el del token
            if rut != token_obj.rut:
                messages.error(request, f"El RUT ingresado no coincide con el RUT invitado ({token_obj.rut}).")
                return render(request, 'voting/militante_register.html', {
                    'form': form,
                    'token_obj': token_obj,
                })
            
            # Crear el militante
            militante = Militante.objects.create(
                nombre=token_obj.nombre,
                rut=token_obj.rut,
                mail=token_obj.mail,
                password=make_password(password)
            )
            
            # Marcar token como usado
            token_obj.used = True
            token_obj.save()
            
            messages.success(request, "¡Registro completado exitosamente! Ahora puedes iniciar sesión para votar.")
            return redirect('voting:index')
    else:
        form = MilitanteRegistrationForm()
    
    context = {
        'form': form,
        'token_obj': token_obj,
    }
    return render(request, 'voting/militante_register.html', context)


@require_http_methods(["GET", "POST"])
def militante_login(request, voting_id):
    """Vista de login para militantes antes de votar"""
    voting = get_object_or_404(Voting, id=voting_id)
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:index')
    
    # Si ya está logueado, redirigir a voting_detail
    session_key = f'militante_{voting_id}'
    if session_key in request.session:
        return redirect('voting:voting_detail', voting_id=voting_id)
    
    contact_email = settings.EMAIL_HOST_USER
    
    if request.method == 'POST':
        form = MilitanteLoginForm(request.POST)
        if not form.is_valid():
            # Si el form no es válido, se queda en la página con los errores
            pass
        else:
            # Procesar login válido
            rut = form.cleaned_data.get('rut')
            password = form.cleaned_data.get('password')
            
            # Buscar militante
            try:
                militante = Militante.objects.get(rut=rut, is_active=True)
            except Militante.DoesNotExist:
                messages.error(
                    request, 
                    f"No estás validado. Contacta a {contact_email}"
                )
                return render(request, 'voting/militante_login.html', {
                    'form': form,
                    'voting': voting,
                    'contact_email': contact_email,
                })
            
            # Verificar contraseña
            if not check_password(password, militante.password):
                messages.error(request, "Contraseña incorrecta.")
                return render(request, 'voting/militante_login.html', {
                    'form': form,
                    'voting': voting,
                    'contact_email': contact_email,
                })
            
            # Verificar que el RUT esté en user_data para esta votación
            try:
                user_data = UserData.objects.get(id_voting=voting, rut=rut)
            except UserData.DoesNotExist:
                messages.error(
                    request, 
                    f"El RUT {rut} no está autorizado para votar en esta votación. Contacte a {contact_email}"
                )
                return render(request, 'voting/militante_login.html', {
                    'form': form,
                    'voting': voting,
                    'contact_email': contact_email,
                })
            
            # Verificar si ya votó
            if user_data.has_voted:
                messages.error(request, "Este RUT ya ha votado en esta votación.")
                return render(request, 'voting/militante_login.html', {
                    'form': form,
                    'voting': voting,
                    'contact_email': contact_email,
                })
            
            # Guardar en sesión
            request.session[session_key] = {
                'rut': rut,
                'mail': militante.mail,
                'name': militante.nombre,
                'lastname': '',
                'user_data_id': user_data.id,
                'militante_id': militante.id,
            }
            request.session.modified = True
            
            messages.success(request, f"¡Bienvenido/a {militante.nombre}! Selecciona una opción para votar.")
            return redirect('voting:voting_detail', voting_id=voting_id)
    else:
        form = MilitanteLoginForm()
    
    context = {
        'form': form,
        'voting': voting,
        'contact_email': contact_email,
    }
    return render(request, 'voting/militante_login.html', context)


def militante_logout(request):
    """Vista de logout para militantes"""
    # Limpiar todas las sesiones de militante
    session_keys_to_remove = []
    for key in request.session.keys():
        if key.startswith('militante_'):
            session_keys_to_remove.append(key)
    
    for key in session_keys_to_remove:
        del request.session[key]
    
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect('voting:index')


@require_http_methods(["GET", "POST"])
def militante_password_reset_request(request, voting_id=None):
    """Vista para solicitar recuperación de contraseña de militante"""
    voting = None
    if voting_id:
        voting = get_object_or_404(Voting, id=voting_id)
    
    if request.method == 'POST':
        form = MilitantePasswordResetRequestForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            
            try:
                militante = Militante.objects.get(rut=rut, is_active=True)
                
                # Crear token de recuperación
                token_obj = MilitantePasswordResetToken.create_token(militante)
                
                # Enviar correo
                base_url = request.build_absolute_uri('/')[:-1]
                reset_link = f"{base_url}/recuperar-contrasena-militante/{token_obj.token}/"
                
                EmailService.send_militante_password_reset_email(
                    to_email=militante.mail,
                    nombre=militante.nombre,
                    reset_link=reset_link
                )
                
                # Ocultar parte del correo
                mail = militante.mail
                visible = mail.split('@')[0][:3]
                hidden_mail = f"{visible}***@{mail.split('@')[1]}"
                
                messages.success(request, f"Se envió un enlace de recuperación a {hidden_mail}")
                
                if voting:
                    return redirect('voting:militante_login', voting_id=voting_id)
                return redirect('voting:index')
                
            except Militante.DoesNotExist:
                # Mostrar mensaje de que no está validado
                contact_email = settings.EMAIL_HOST_USER
                messages.error(request, f"No estás validado. Contacta a {contact_email}")
                if voting:
                    return redirect('voting:militante_password_reset_request', voting_id=voting_id)
                return redirect('voting:index')
    else:
        form = MilitantePasswordResetRequestForm()
    
    contact_email = settings.EMAIL_HOST_USER
    
    context = {
        'form': form,
        'voting': voting,
        'contact_email': contact_email,
    }
    return render(request, 'voting/militante_password_reset_request.html', context)


@require_http_methods(["GET", "POST"])
def militante_password_reset(request, token):
    """Vista para restablecer contraseña de militante"""
    try:
        token_obj = MilitantePasswordResetToken.objects.get(token=token)
    except MilitantePasswordResetToken.DoesNotExist:
        messages.error(request, "El enlace de recuperación no es válido.")
        return redirect('voting:index')
    
    if not token_obj.is_valid():
        messages.error(request, "El enlace de recuperación ha expirado o ya fue utilizado.")
        return redirect('voting:index')
    
    if request.method == 'POST':
        form = MilitantePasswordResetForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data.get('password')
            
            # Actualizar contraseña
            militante = token_obj.militante
            militante.password = make_password(password)
            militante.save()
            
            # Marcar token como usado
            token_obj.used = True
            token_obj.save()
            
            messages.success(request, "¡Contraseña restablecida exitosamente! Ahora puedes iniciar sesión.")
            return redirect('voting:index')
    else:
        form = MilitantePasswordResetForm()
    
    context = {
        'form': form,
        'token_obj': token_obj,
    }
    return render(request, 'voting/militante_password_reset.html', context)
