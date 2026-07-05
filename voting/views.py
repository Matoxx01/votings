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
from voting.forms import VoterRegistrationForm, MilitanteRegistrationForm, MilitanteLoginForm, MilitantePasswordResetRequestForm, MilitantePasswordResetForm, MilitanteEditProfileForm, ReenviarRegistroForm
from voting.services import EmailService
from voting.time_utils import get_real_now
from voting.rate_limit import rate_limit_check, record_attempt, rate_limit_json


@require_http_methods(["GET", "POST"])
def vota(request):
    """Vista de login unificado para votar (reemplaza la antigua lista de regiones)"""
    # Si ya está logueado para votar, redirigir a votaciones pendientes
    if 'voting_session' in request.session:
        return redirect('voting:votaciones_pendientes')

    contact_email = 'contacto@partidorepublicanodechile.cl'

    if request.method == 'POST':
        # Rate limiting: 5 intentos / 5 min
        limited, wait = rate_limit_check(request, 'login_militante', 5, 300)
        if limited:
            messages.error(request, f"Demasiados intentos. Espera {wait} segundos antes de intentar nuevamente.")
            return render(request, 'voting/vota.html', {
                'form': MilitanteLoginForm(),
                'contact_email': contact_email,
            })
        form = MilitanteLoginForm(request.POST)
        if form.is_valid():
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
                return render(request, 'voting/vota.html', {
                    'form': form,
                    'contact_email': contact_email,
                })

            # Verificar contraseña
            if not check_password(password, militante.password):
                record_attempt(request, 'login_militante', 300)
                messages.error(request, "Contraseña incorrecta.")
                return render(request, 'voting/vota.html', {
                    'form': form,
                    'contact_email': contact_email,
                })

            # Verificar si hay votaciones pendientes para este usuario
            now = get_real_now()
            pending_user_data = UserData.objects.filter(
                rut=rut,
                has_voted=False,
                id_voting__start_date__lte=now,
                id_voting__finish_date__gte=now,
            ).select_related('id_voting')

            if not pending_user_data.exists():
                # Verificar si tiene votaciones pero ya votó en todas
                all_user_data = UserData.objects.filter(
                    rut=rut,
                    id_voting__start_date__lte=now,
                    id_voting__finish_date__gte=now,
                )
                if all_user_data.exists():
                    messages.info(request, "Ya has completado todas tus votaciones.")
                    return redirect('voting:success')
                else:
                    messages.error(
                        request,
                        f"No tienes votaciones disponibles en este momento. Contacta a {contact_email}"
                    )
                    return render(request, 'voting/vota.html', {
                        'form': form,
                        'contact_email': contact_email,
                    })

            # Guardar sesión unificada de votación
            request.session['voting_session'] = {
                'rut': rut,
                'mail': militante.mail,
                'name': militante.nombre,
                'militante_id': militante.id,
            }
            request.session.modified = True

            messages.success(request, f"¡Bienvenido/a {militante.nombre}!")
            return redirect('voting:votaciones_pendientes')
    else:
        form = MilitanteLoginForm()

    context = {
        'form': form,
        'contact_email': contact_email,
    }
    return render(request, 'voting/vota.html', context)


def votaciones_pendientes(request):
    """Vista que muestra las votaciones pendientes del usuario logueado"""
    session_data = request.session.get('voting_session')
    if not session_data:
        messages.error(request, "Debes iniciar sesión para votar.")
        return redirect('voting:vota')

    rut = session_data.get('rut')
    now = get_real_now()

    pending_user_data = UserData.objects.filter(
        rut=rut,
        has_voted=False,
        id_voting__start_date__lte=now,
        id_voting__finish_date__gte=now,
    ).select_related('id_voting').order_by('id_voting__start_date')

    pending_votings = [ud.id_voting for ud in pending_user_data]

    if not pending_votings:
        # Ya completó todas, mostrar éxito
        if 'voting_session' in request.session:
            del request.session['voting_session']
            request.session.modified = True
        messages.success(request, "¡Has completado todas tus votaciones!")
        return redirect('voting:success')

    first_voting = pending_votings[0]

    context = {
        'pending_votings': pending_votings,
        'first_voting_id': first_voting.id,
        'militante_name': session_data.get('name', 'Usuario'),
        'total_count': len(pending_votings),
    }
    return render(request, 'voting/votaciones_pendientes.html', context)


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
        elif path.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        
        response = FileResponse(open(media_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{media_path.name}"'
        return response
    
    return HttpResponse(status=404)


def biblioteca(request):
    """Vista de la Biblioteca y Documentos"""
    from voting.models import DocumentSection
    sections = DocumentSection.objects.prefetch_related('documents').filter(is_active=True)
    return render(request, 'voting/biblioteca.html', {'sections': sections})



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
        return redirect('voting:votaciones_pendientes')
    
    # Verificar sesión unificada de votación
    session_data = request.session.get('voting_session')
    if not session_data:
        return redirect('voting:vota')
    
    # Verificar que el usuario está autorizado para esta votación
    rut = session_data.get('rut')
    try:
        user_data = UserData.objects.get(id_voting=voting, rut=rut)
    except UserData.DoesNotExist:
        messages.error(request, "No estás autorizado para votar en esta votación.")
        return redirect('voting:votaciones_pendientes')
    
    if user_data.has_voted:
        messages.info(request, "Ya has votado en esta votación.")
        return redirect('voting:votaciones_pendientes')
    
    subjects = voting.subjects.exclude(name='Voto en Blanco')
    
    context = {
        'voting': voting,
        'subjects': subjects,
    }
    return render(request, 'voting/voting_detail.html', context)


@require_http_methods(["GET", "POST"])
def register(request, voting_id):
    """Vista legacy - redirige al login unificado"""
    return redirect('voting:vota')


@require_http_methods(["GET", "POST"])
def vote(request, subject_id):
    """Vista para confirmar y votar"""
    subject = get_object_or_404(Subject, id=subject_id)
    voting = subject.id_voting
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:votaciones_pendientes')
    
    # Verificar sesión unificada de votación
    session_data = request.session.get('voting_session')
    if not session_data:
        messages.error(request, "Debes iniciar sesión para votar.")
        return redirect('voting:vota')
    
    # Obtener user_data para esta votación
    rut = session_data.get('rut')
    try:
        user_data = UserData.objects.get(id_voting=voting, rut=rut)
    except UserData.DoesNotExist:
        messages.error(request, "No estás autorizado para votar en esta votación.")
        return redirect('voting:votaciones_pendientes')
    
    voter_data = {
        'rut': rut,
        'mail': session_data.get('mail'),
        'name': session_data.get('name'),
        'lastname': '',
        'user_data_id': user_data.id,
    }
    
    if request.method == 'POST':
        return process_vote(request, voting, subject, voter_data)
    
    context = {
        'voting': voting,
        'subject': subject,
        'voter_name': session_data.get('name', ''),
    }
    return render(request, 'voting/vote.html', context)


@require_http_methods(["POST"])
def vote_blank(request, voting_id):
    """Procesa un voto en blanco"""
    voting = get_object_or_404(Voting, id=voting_id)

    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:votaciones_pendientes')

    # Verificar sesión unificada de votación
    session_data = request.session.get('voting_session')
    if not session_data:
        messages.error(request, "Debes iniciar sesión para votar.")
        return redirect('voting:vota')

    # Obtener user_data para esta votación
    rut = session_data.get('rut')
    try:
        user_data = UserData.objects.get(id_voting=voting, rut=rut)
    except UserData.DoesNotExist:
        messages.error(request, "No estás autorizado para votar en esta votación.")
        return redirect('voting:votaciones_pendientes')

    voter_data = {
        'rut': rut,
        'mail': session_data.get('mail'),
        'name': session_data.get('name'),
        'lastname': '',
        'user_data_id': user_data.id,
    }

    # Obtener o crear el subject "Voto en Blanco" para esta votación
    blank_subject, _ = Subject.objects.get_or_create(
        name='Voto en Blanco',
        id_voting=voting,
    )

    return process_vote(request, voting, blank_subject, voter_data)


@transaction.atomic
def process_vote(request, voting, subject, voter_data):
    """
    Procesa el voto del usuario.
    Después de registrar el voto, verifica si hay más votaciones pendientes
    y redirige a la siguiente o a la página de éxito final.
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
        return redirect('voting:vota')
    
    # Validar que el usuario no ha votado
    if user_data.has_voted:
        messages.error(request, "Este RUT ya ha votado en esta votación.")
        return redirect('voting:votaciones_pendientes')
    
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
        
        # Enviar correo de confirmación (por cada votación completada)
        try:
            EmailService.send_confirmation_email(
                to_email=mail,
                user_name=f"{name} {lastname}",
                voting_title=voting.title,
            )
        except Exception:
            pass
        
        # Verificar si hay más votaciones pendientes
        now = get_real_now()
        next_pending = UserData.objects.filter(
            rut=rut,
            has_voted=False,
            id_voting__start_date__lte=now,
            id_voting__finish_date__gte=now,
        ).select_related('id_voting').order_by('id_voting__start_date').first()
        
        if next_pending:
            # Hay más votaciones, continuar con la siguiente
            messages.success(request, f"¡Voto registrado en '{voting.title}'! Continuando con la siguiente votación...")
            return redirect('voting:voting_detail', voting_id=next_pending.id_voting.id)
        else:
            # Todas las votaciones completadas, limpiar sesión y mostrar éxito
            if 'voting_session' in request.session:
                del request.session['voting_session']
                request.session.modified = True
            messages.success(request, "¡Has completado todas tus votaciones!")
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
    """Vista de login para militantes - redirige al login unificado"""
    return redirect('voting:vota')


def militante_logout(request):
    """Vista de logout para militantes"""
    # Limpiar todas las sesiones de militante
    session_keys_to_remove = []
    for key in request.session.keys():
        if key.startswith('militante_'):
            session_keys_to_remove.append(key)
    
    for key in session_keys_to_remove:
        del request.session[key]
    
    # Limpiar sesión unificada de votación
    if 'voting_session' in request.session:
        del request.session['voting_session']
    
    request.session.modified = True
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
                    return redirect('voting:vota')
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


@require_http_methods(["GET", "POST"])
def reenviar_registro(request):
    """Vista para solicitar el reenvío del correo de registro en sistema para militantes pendientes"""
    contact_email = 'contacto@partidorepublicanodechile.cl'
    sent_mail = None
    resent_already = False
    
    if request.method == 'POST':
        # Rate limiting: 5 intentos / 5 min
        limited, wait = rate_limit_check(request, 'reenviar_registro', 5, 300)
        if limited:
            messages.error(request, f"Demasiados intentos. Espera {wait} segundos antes de intentar nuevamente.")
            return render(request, 'voting/reenviar_registro.html', {
                'form': ReenviarRegistroForm(),
                'contact_email': contact_email,
            })
            
        form = ReenviarRegistroForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            
            # 1. Verificar si ya es un militante completamente registrado
            if Militante.objects.filter(rut=rut, is_active=True).exists():
                messages.info(request, "Este RUT ya está completamente registrado en el sistema. Puedes iniciar sesión en 'Edita tu usuario' o para votar.")
                return redirect('voting:vota')
                
            # 2. Buscar si tiene un token de registro pendiente (militante pendiente de registro)
            token_obj = MilitanteRegistrationToken.objects.filter(rut=rut, used=False).order_by('-created_at').first()
            
            if not token_obj:
                record_attempt(request, 'reenviar_registro', 300)
                messages.error(request, f"No se encontró un registro pendiente para este RUT en la base de datos. Si crees que es un error, contacta a {contact_email}")
                return render(request, 'voting/reenviar_registro.html', {
                    'form': form,
                    'contact_email': contact_email,
                })
                
            # 3. Verificar si ya se ha reenviado el registro (Límite 1 vez por usuario)
            sent_mail = token_obj.mail
            if token_obj.resent:
                resent_already = True
                messages.warning(request, "Ya se ha realizado el reenvío de registro para este usuario (límite de 1 reenvío por usuario).")
            else:
                # Proceder con el reenvío
                base_url = f"{request.scheme}://{request.get_host()}"
                registration_link = f"{base_url}/registro-militante/{token_obj.token}/"
                
                try:
                    EmailService.send_militante_registration_email(
                        to_email=token_obj.mail,
                        nombre=token_obj.nombre,
                        registration_link=registration_link
                    )
                    token_obj.resent = True
                    token_obj.save()
                    messages.success(request, "¡Correo de registro reenviado exitosamente!")
                except Exception as e:
                    messages.error(request, f"Error al enviar el correo: {str(e)}")
                    sent_mail = None
    else:
        form = ReenviarRegistroForm()
        
    context = {
        'form': form,
        'contact_email': contact_email,
        'sent_mail': sent_mail,
        'resent_already': resent_already,
    }
    return render(request, 'voting/reenviar_registro.html', context)
