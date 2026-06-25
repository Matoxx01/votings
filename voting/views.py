def vota(request):
    """Vista para mostrar las votaciones y regiones en /vota"""
    now = get_real_now()
    regions_with_votings = Region.objects.filter(
        votings__start_date__lte=now,
        votings__finish_date__gte=now
    ).exclude(id=17).distinct().order_by('id')
    votings_without_region = Voting.objects.filter(
        id_region__id=17,
        start_date__lte=now,
        finish_date__gte=now
    ).order_by('-created_at')
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
    return render(request, 'voting/vota.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from pathlib import Path
import io
import json
import random
from voting.models import Voting, Subject, UserData, Count, VotingRecord, Region, Militante, MilitanteRegistrationToken, MilitantePasswordResetToken
from voting.forms import VoterRegistrationForm, MilitanteRegistrationForm, MilitanteLoginForm, MilitantePasswordResetRequestForm, MilitantePasswordResetForm, MilitanteEditProfileForm
from voting.services import EmailService
from voting.time_utils import get_real_now
from voting.rate_limit import rate_limit_check, record_attempt, rate_limit_json


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
    
    has_active_votings = regions_with_votings.exists() or votings_without_region.exists()

    context = {
        'regions': regions_with_votings,
        'votings_without_region': votings_without_region,
        'militante_logged_in': militante_logged_in,
        'militante_name': militante_name,
        'has_active_votings': has_active_votings,
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
    
    subjects = voting.subjects.exclude(name='Voto en Blanco')
    
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


@require_http_methods(["POST"])
def vote_blank(request, voting_id):
    """Procesa un voto en blanco"""
    voting = get_object_or_404(Voting, id=voting_id)

    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:voting_detail', voting_id=voting.id)

    session_key = f'militante_{voting_id}'
    if session_key not in request.session:
        messages.error(request, "Debes iniciar sesión para votar.")
        return redirect('voting:militante_login', voting_id=voting_id)

    voter_data = request.session.get(session_key, {})

    # Obtener o crear el subject "Voto en Blanco" para esta votación
    blank_subject, _ = Subject.objects.get_or_create(
        name='Voto en Blanco',
        id_voting=voting,
    )

    return process_vote(request, voting, blank_subject, voter_data)


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
    
    # Obtener el user_data con bloqueo de fila para evitar Race Conditions (doble voto)
    try:
        user_data = UserData.objects.select_for_update().get(id=user_data_id)
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
        
        # Incrementar contador atómicamente
        count, created = Count.objects.get_or_create(id_subject=subject)
        Count.objects.filter(id_subject=subject).update(number=F('number') + 1)
        
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
        votes = VotingRecord.objects.filter(id_subject=subject).count()
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
        messages.error(request, "El enlace de registro ya fue utilizado.")
        return redirect('voting:index')
    
    # Verificar si el RUT ya está registrado
    if Militante.objects.filter(rut=token_obj.rut).exists():
        messages.error(request, "Este RUT ya está registrado en el sistema.")
        token_obj.used = True
        token_obj.save()
        return redirect('voting:index')
    
    if request.method == 'POST':
        form = MilitanteRegistrationForm(request.POST)
        form._http_request = request  # Para rate limiting de API Registro Civil
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
            
            # Determinar el correo a utilizar
            final_mail = token_obj.mail
            cambiar_correo = request.POST.get('check_cambiar_correo') == 'on'
            
            if cambiar_correo:
                if request.session.get('correo_cambiado_verificado'):
                    nuevo_correo = request.session.get('nuevo_correo_verificado')
                    if nuevo_correo:
                        final_mail = nuevo_correo
                        # Limpiar la sesión para que no afecte futuros registros
                        del request.session['correo_cambiado_verificado']
                        del request.session['nuevo_correo_verificado']
                else:
                    messages.error(request, "Has marcado la opción de cambiar correo, pero la verificación está incompleta.")
                    return render(request, 'voting/militante_register.html', {
                        'form': form,
                        'token_obj': token_obj,
                    })

            # Crear el militante
            militante = Militante.objects.create(
                nombre=token_obj.nombre,
                rut=token_obj.rut,
                mail=final_mail,
                password=make_password(password)
            )
            
            # Marcar token como usado
            token_obj.used = True
            token_obj.save()
            
            # Enviar correo de bienvenida / confirmación de registro
            try:
                EmailService.send_militante_welcome_email(militante.mail, militante.nombre)
            except Exception:
                pass
            
            # Notificar votaciones donde el militante está habilitado (futuras o en curso)
            now = get_real_now()
            active_or_upcoming_votings = Voting.objects.filter(
                user_data__rut=militante.rut,
                finish_date__gt=now,
            ).distinct()
            
            import pytz
            santiago_tz = pytz.timezone('America/Santiago')
            
            for voting in active_or_upcoming_votings:
                if voting.start_date > now:
                    # La votación aún no comienza (Votación próxima)
                    try:
                        EmailService.send_upcoming_voting_email(
                            to_email=militante.mail,
                            nombre=militante.nombre,
                            voting_title=voting.title,
                            voting_description=voting.description,
                            start_date=voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M'),
                            finish_date=voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M'),
                            candidates=voting.subjects.all(),
                        )
                    except Exception:
                        pass
                else:
                    # La votación ya inició y está en curso
                    try:
                        EmailService.send_voting_reminder_email(
                            to_email=militante.mail,
                            user_name=militante.nombre,
                            voting_title=voting.title,
                        )
                    except Exception:
                        pass
            
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
    
    contact_email = 'contacto@partidorepublicanodechile.cl'
    
    if request.method == 'POST':
        # Rate limiting: 5 intentos / 5 min
        limited, wait = rate_limit_check(request, 'login_militante', 5, 300)
        if limited:
            messages.error(request, f"Demasiados intentos. Espera {wait} segundos antes de intentar nuevamente.")
            return render(request, 'voting/militante_login.html', {
                'form': MilitanteLoginForm(),
                'voting': voting,
                'contact_email': contact_email,
            })
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
                record_attempt(request, 'login_militante', 300)
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
                record_attempt(request, 'login_militante', 300)
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
        # Rate limiting: 3 solicitudes / 10 min
        limited, wait = rate_limit_check(request, 'reset_militante', 3, 600)
        if limited:
            messages.error(request, f"Demasiados intentos. Espera {wait} segundos.")
            if voting:
                return redirect('voting:militante_password_reset_request', voting_id=voting_id)
            return redirect('voting:index')
        form = MilitantePasswordResetRequestForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            
            try:
                militante = Militante.objects.get(rut=rut, is_active=True)
                
                # Crear token de recuperación
                token_obj = MilitantePasswordResetToken.create_token(militante)
                record_attempt(request, 'reset_militante', 600)
                
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
                contact_email = 'contacto@partidorepublicanodechile.cl'
                messages.error(request, f"No estás validado. Contacta a {contact_email}")
                if voting:
                    return redirect('voting:militante_password_reset_request', voting_id=voting_id)
                return redirect('voting:index')
    else:
        form = MilitantePasswordResetRequestForm()
    
    contact_email = 'contacto@partidorepublicanodechile.cl'
    
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

from django.http import JsonResponse

@require_http_methods(["POST"])
@rate_limit_json('envio_codigo', max_attempts=3, window_seconds=300)
def enviar_codigo_correo(request):
    """Genera y envía un código de verificación por correo via AJAX"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Correo inválido.'})
        
        if Militante.objects.filter(mail=email).exists():
            return JsonResponse({'success': False, 'message': 'Este correo ya está registrado en el sistema.'})
        
        # Generar código de 6 dígitos
        code = f"{random.randint(100000, 999999)}"
        
        # Guardar en sesión con timestamp de expiración (5 minutos)
        import time as _time
        request.session['verification_code'] = code
        request.session['verification_email'] = email
        request.session['verification_code_expires'] = _time.time() + 300
        request.session.modified = True
        
        # Registrar intento para rate limiting
        record_attempt(request, 'envio_codigo', 300)
        
        # Enviar correo
        EmailService.send_verification_code_email(email, code)
        
        return JsonResponse({'success': True, 'message': 'Código enviado exitosamente.'})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error al enviar el código. Intenta más tarde.'})

@require_http_methods(["POST"])
@rate_limit_json('validar_codigo', max_attempts=3, window_seconds=300)
def validar_codigo_correo(request):
    """Valida el código asíncronamente y guarda estado verificado en sesión"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        code = data.get('code')
        
        session_code = request.session.get('verification_code')
        session_email = request.session.get('verification_email')
        code_expires = request.session.get('verification_code_expires', 0)
        
        if not session_code or not session_email:
            return JsonResponse({'success': False, 'message': 'No hay código pendiente. Envíe uno nuevo.'})
        
        # Verificar expiración del código (5 minutos)
        import time as _time
        if _time.time() > code_expires:
            # Limpiar código expirado
            for k in ('verification_code', 'verification_email', 'verification_code_expires'):
                request.session.pop(k, None)
            request.session.modified = True
            return JsonResponse({'success': False, 'message': 'El código ha expirado. Solicita uno nuevo.'})
        
        # Registrar intento para rate limiting
        record_attempt(request, 'validar_codigo', 300)
        
        if email == session_email and str(code) == str(session_code):
            request.session['correo_cambiado_verificado'] = True
            request.session['nuevo_correo_verificado'] = email
            request.session.modified = True
            # Limpiamos código usado
            for k in ('verification_code', 'verification_email', 'verification_code_expires'):
                request.session.pop(k, None)
            return JsonResponse({'success': True, 'message': 'Correo verificado exitosamente.'})
        else:
            return JsonResponse({'success': False, 'message': 'Código o correo incorrecto.'})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error al validar. Intenta más tarde.'})


@require_http_methods(["GET", "POST"])
def militante_general_login(request):
    """Vista de login general para militantes (para editar usuario)"""
    # Si ya está logueado, redirigir a editar perfil
    for key in request.session.keys():
        if key.startswith('militante_'):
            return redirect('voting:militante_edit_profile')
    
    contact_email = 'contacto@partidorepublicanodechile.cl'
    
    if request.method == 'POST':
        limited, wait = rate_limit_check(request, 'login_militante', 5, 300)
        if limited:
            messages.error(request, f"Demasiados intentos. Espera {wait} segundos antes de intentar nuevamente.")
            return render(request, 'voting/militante_general_login.html', {
                'form': MilitanteLoginForm(),
                'contact_email': contact_email,
            })
        form = MilitanteLoginForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            password = form.cleaned_data.get('password')
            
            try:
                militante = Militante.objects.get(rut=rut, is_active=True)
            except Militante.DoesNotExist:
                record_attempt(request, 'login_militante', 300)
                messages.error(
                    request, 
                    f"No estás validado. Contacta a {contact_email}"
                )
                return render(request, 'voting/militante_general_login.html', {
                    'form': form,
                    'contact_email': contact_email,
                })
            
            if not check_password(password, militante.password):
                record_attempt(request, 'login_militante', 300)
                messages.error(request, "Contraseña incorrecta.")
                return render(request, 'voting/militante_general_login.html', {
                    'form': form,
                    'contact_email': contact_email,
                })
            
            # Guardar en sesión general de militante
            request.session['militante_general'] = {
                'rut': rut,
                'mail': militante.mail,
                'name': militante.nombre,
                'lastname': '',
                'militante_id': militante.id,
            }
            request.session.modified = True
            
            messages.success(request, f"¡Bienvenido/a {militante.nombre}! Puedes actualizar tus datos a continuación.")
            return redirect('voting:militante_edit_profile')
    else:
        form = MilitanteLoginForm()
    
    context = {
        'form': form,
        'contact_email': contact_email,
    }
    return render(request, 'voting/militante_general_login.html', context)


@require_http_methods(["GET", "POST"])
def militante_edit_profile(request):
    """Vista para que un militante edite sus datos (correo, nombre, contraseña) sin cambiar RUT"""
    militante_data = None
    session_key = None
    for key in request.session.keys():
        if key.startswith('militante_'):
            militante_data = request.session[key]
            session_key = key
            break
            
    if not militante_data or 'rut' not in militante_data:
        messages.error(request, "Debes iniciar sesión para editar tus datos.")
        return redirect('voting:militante_general_login')
        
    rut = militante_data.get('rut')
    try:
        militante = Militante.objects.get(rut=rut, is_active=True)
    except Militante.DoesNotExist:
        messages.error(request, "Usuario no encontrado o inactivo.")
        return redirect('voting:militante_logout')
        
    if request.method == 'POST':
        form = MilitanteEditProfileForm(request.POST, militante_rut=militante.rut)
        if form.is_valid():
            nombre = form.cleaned_data.get('nombre')
            password = form.cleaned_data.get('password')
            
            # Verificar si quiere cambiar correo
            cambiar_correo = request.POST.get('check_cambiar_correo') == 'on'
            final_mail = militante.mail
            
            if cambiar_correo:
                if request.session.get('correo_cambiado_verificado'):
                    nuevo_correo = request.session.get('nuevo_correo_verificado')
                    if nuevo_correo:
                        if Militante.objects.filter(mail=nuevo_correo).exclude(rut=militante.rut).exists():
                            messages.error(request, "El nuevo correo ya está siendo utilizado por otro usuario.")
                            return render(request, 'voting/militante_edit_profile.html', {
                                'form': form,
                                'militante': militante,
                                'militante_logged_in': True,
                                'militante_name': militante_data.get('name', militante.nombre),
                            })
                        final_mail = nuevo_correo
                        del request.session['correo_cambiado_verificado']
                        del request.session['nuevo_correo_verificado']
                else:
                    messages.error(request, "Has marcado la opción de cambiar correo, pero la verificación está incompleta.")
                    return render(request, 'voting/militante_edit_profile.html', {
                        'form': form,
                        'militante': militante,
                        'militante_logged_in': True,
                        'militante_name': militante_data.get('name', militante.nombre),
                    })
            
            militante.nombre = nombre
            militante.mail = final_mail
            if password:
                militante.password = make_password(password)
            militante.save()
            
            # Actualizar datos en la sesión
            request.session[session_key]['name'] = nombre
            request.session[session_key]['mail'] = final_mail
            request.session.modified = True
            
            messages.success(request, "¡Tus datos han sido actualizados correctamente!")
            return redirect('voting:index')
    else:
        form = MilitanteEditProfileForm(initial={
            'nombre': militante.nombre,
            'rut': militante.rut,
            'mail': militante.mail,
        })
        
    context = {
        'form': form,
        'militante': militante,
        'militante_logged_in': True,
        'militante_name': militante_data.get('name', militante.nombre),
    }
    return render(request, 'voting/militante_edit_profile.html', context)
