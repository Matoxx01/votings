from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from voting.models import Voting, Subject, UserData, Count, VotingRecord
from voting.forms import VoterRegistrationForm
from voting.services import EmailService


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
    
    subjects = voting.subjects.all()
    
    context = {
        'voting': voting,
        'subjects': subjects,
    }
    return render(request, 'voting/voting_detail.html', context)


@require_http_methods(["GET", "POST"])
def vote(request, subject_id):
    """Vista para registrarse y votar"""
    subject = get_object_or_404(Subject, id=subject_id)
    voting = subject.id_voting
    
    if not voting.is_open():
        messages.error(request, "Esta votación no está disponible en este momento.")
        return redirect('voting:voting_detail', voting_id=voting.id)
    
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            return process_vote(request, form, voting, subject)
    else:
        form = VoterRegistrationForm(initial={'subject': subject.id})
    
    context = {
        'form': form,
        'voting': voting,
        'subject': subject,
    }
    return render(request, 'voting/vote.html', context)


@transaction.atomic
def process_vote(request, form, voting, subject):
    """
    Procesa el voto del usuario
    """
    rut = form.cleaned_data.get('rut')
    mail = form.cleaned_data.get('mail')
    name = form.cleaned_data.get('name')
    lastname = form.cleaned_data.get('lastname')
    
    # Validar que el RUT existe en user_data
    try:
        user_data = UserData.objects.get(id_voting=voting, rut=rut)
    except UserData.DoesNotExist:
        messages.error(request, f"El RUT {rut} no está registrado para esta votación.")
        return redirect('voting:vote', subject_id=subject.id)
    
    # Validar que el usuario no ha votado
    if user_data.has_voted:
        messages.error(request, "Este RUT ya ha votado en esta votación.")
        return redirect('voting:voting_detail', voting_id=voting.id)
    
    try:
        # Registrar el voto
        voting_record = VotingRecord.objects.create(
            id_voting=voting,
            id_subject=subject,
            user_data=user_data,
            rut=rut,
            mail=mail,
        )
        
        # Incrementar contador
        count, created = Count.objects.get_or_create(id_subject=subject)
        count.number += 1
        count.save()
        
        # Marcar como votado
        user_data.has_voted = True
        user_data.voted_at = timezone.now()
        user_data.save()
        
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
