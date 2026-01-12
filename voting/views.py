from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.conf import settings
from pathlib import Path
import io
from voting.models import Voting, Subject, UserData, Count, VotingRecord
from voting.forms import VoterRegistrationForm
from voting.services import EmailService


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
    """Vista principal de votaciones"""
    votings = Voting.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'votings': votings,
    }
    return render(request, 'voting/index.html', context)


def voting_detail(request, voting_id):
    """Vista de detalle de una votación con sus subjects"""
    voting = get_object_or_404(Voting, id=voting_id, is_active=True)
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:index')
    
    # Verificar si el usuario ya está registrado en esta votación
    session_key = f'voter_{voting_id}'
    if session_key not in request.session:
        # Redirigir a registro si no está registrado
        return redirect('voting:register', voting_id=voting_id)
    
    subjects = voting.subjects.all()
    
    context = {
        'voting': voting,
        'subjects': subjects,
    }
    return render(request, 'voting/voting_detail.html', context)


@require_http_methods(["GET", "POST"])
def register(request, voting_id):
    """Vista para registrarse antes de votar"""
    voting = get_object_or_404(Voting, id=voting_id, is_active=True)
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:index')
    
    # Si ya está registrado, redirigir a voting_detail
    session_key = f'voter_{voting_id}'
    if session_key in request.session:
        return redirect('voting:voting_detail', voting_id=voting_id)
    
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data.get('rut')
            mail = form.cleaned_data.get('mail')
            name = form.cleaned_data.get('name')
            lastname = form.cleaned_data.get('lastname')
            
            # Validar que el RUT existe en user_data
            try:
                user_data = UserData.objects.get(id_voting=voting, rut=rut)
            except UserData.DoesNotExist:
                messages.error(request, f"El RUT {rut} no está registrado para esta votación.")
                return redirect('voting:register', voting_id=voting_id)
            
            # Validar que el usuario no ha votado
            if user_data.has_voted:
                messages.error(request, "Este RUT ya ha votado en esta votación.")
                return redirect('voting:index')
            
            # Guardar datos en sesión
            request.session[session_key] = {
                'rut': rut,
                'mail': mail,
                'name': name,
                'lastname': lastname,
                'user_data_id': user_data.id,
            }
            request.session.modified = True
            
            messages.success(request, "¡Registro completado! Ahora selecciona una opción para votar.")
            return redirect('voting:voting_detail', voting_id=voting_id)
    else:
        form = VoterRegistrationForm()
    
    context = {
        'form': form,
        'voting': voting,
    }
    return render(request, 'voting/register.html', context)


@require_http_methods(["GET", "POST"])
def vote(request, subject_id):
    """Vista para confirmar y votar"""
    subject = get_object_or_404(Subject, id=subject_id)
    voting = subject.id_voting
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:voting_detail', voting_id=voting.id)
    
    # Verificar si el usuario está registrado en sesión
    session_key = f'voter_{voting.id}'
    if session_key not in request.session:
        messages.error(request, "Debes registrarte primero para votar.")
        return redirect('voting:register', voting_id=voting.id)
    
    voter_data = request.session.get(session_key, {})
    
    if request.method == 'POST':
        return process_vote(request, voting, subject, voter_data)
    
    context = {
        'voting': voting,
        'subject': subject,
        'voter_name': f"{voter_data.get('name')} {voter_data.get('lastname')}",
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
    lastname = voter_data.get('lastname')
    user_data_id = voter_data.get('user_data_id')
    
    # Obtener el user_data
    try:
        user_data = UserData.objects.get(id=user_data_id)
    except UserData.DoesNotExist:
        messages.error(request, "Error: No se encontraron los datos de registro.")
        return redirect('voting:register', voting_id=voting.id)
    
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
        user_data.voted_at = timezone.now()
        user_data.save()
        
        # Limpiar sesión de registro
        session_key = f'voter_{voting.id}'
        if session_key in request.session:
            del request.session[session_key]
            request.session.modified = True
        
        # Enviar correo de confirmación
        try:
            EmailService.send_confirmation_email(
                to_email=mail,
                user_name=f"{name} {lastname}",
                voting_title=voting.title,
                subject_name=subject.name,
            )
        except Exception as e:
            print(f"Error al enviar correo: {e}")
        
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
