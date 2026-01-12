from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count as DbCount, Q
from django.utils import timezone
from voting.models import Maintainer, Voting, Subject, UserData, VotingRecord, Count, Role
from dashboard.forms import MaintainerLoginForm, VotingForm, SubjectForm, UserDataUploadForm
from dashboard.decorators import maintainer_login_required
from dashboard.services import ExcelService
import json


def login_view(request):
    """Vista de login para maintainers"""
    if request.session.get('maintainer_id'):
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = MaintainerLoginForm(request.POST)
        if form.is_valid():
            mail = form.cleaned_data.get('mail')
            password = form.cleaned_data.get('password')
            
            try:
                maintainer = Maintainer.objects.get(mail=mail, is_active=True)
                # En producción, usar check_password
                if maintainer.password == password:
                    request.session['maintainer_id'] = maintainer.id
                    request.session['maintainer_name'] = f"{maintainer.name} {maintainer.lastname}"
                    messages.success(request, f"Bienvenido, {maintainer.name}!")
                    return redirect('dashboard:dashboard')
                else:
                    messages.error(request, "Contraseña incorrecta.")
            except Maintainer.DoesNotExist:
                messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = MaintainerLoginForm()
    
    context = {
        'form': form,
    }
    return render(request, 'dashboard/login.html', context)


def logout_view(request):
    """Vista de logout para maintainers"""
    if 'maintainer_id' in request.session:
        del request.session['maintainer_id']
    if 'maintainer_name' in request.session:
        del request.session['maintainer_name']
    
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect('dashboard:login')


@maintainer_login_required
def dashboard(request):
    """Vista principal del dashboard"""
    total_votings = Voting.objects.count()
    active_votings = Voting.objects.filter(
        start_date__lte=timezone.now(),
        finish_date__gte=timezone.now(),
        is_active=True
    ).count()
    total_votes = VotingRecord.objects.count()
    
    context = {
        'total_votings': total_votings,
        'active_votings': active_votings,
        'total_votes': total_votes,
    }
    return render(request, 'dashboard/dashboard.html', context)


@maintainer_login_required
def votings_management(request):
    """Vista para gestionar votaciones"""
    votings = Voting.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        form = VotingForm(request.POST, request.FILES)
        if form.is_valid():
            voting = form.save()
            messages.success(request, f"Votación '{voting.title}' creada correctamente.")
            return redirect('dashboard:votings_management')
    else:
        form = VotingForm()
    
    context = {
        'votings': votings,
        'form': form,
    }
    return render(request, 'dashboard/votings_management.html', context)


@maintainer_login_required
def voting_detail(request, voting_id):
    """Vista de detalle de una votación en el dashboard"""
    voting = get_object_or_404(Voting, id=voting_id)
    subjects = voting.subjects.all()
    
    stats = []
    total_votes = 0
    
    for subject in subjects:
        count = Count.objects.filter(id_subject=subject).first()
        votes = count.number if count else 0
        total_votes += votes
        stats.append({
            'subject': subject,
            'votes': votes,
        })
    
    context = {
        'voting': voting,
        'subjects': subjects,
        'stats': stats,
        'total_votes': total_votes,
    }
    return render(request, 'dashboard/voting_detail.html', context)


@maintainer_login_required
def subjects_management(request, voting_id):
    """Vista para gestionar subjects de una votación"""
    voting = get_object_or_404(Voting, id=voting_id)
    subjects = voting.subjects.all()
    
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.id_voting = voting
            subject.save()
            
            # Crear contador para el subject
            Count.objects.get_or_create(id_subject=subject)
            
            messages.success(request, f"Subject '{subject.name}' creado correctamente.")
            return redirect('dashboard:subjects_management', voting_id=voting_id)
    else:
        form = SubjectForm()
    
    context = {
        'voting': voting,
        'subjects': subjects,
        'form': form,
    }
    return render(request, 'dashboard/subjects_management.html', context)


@maintainer_login_required
def user_data_management(request):
    """Vista para gestionar datos de usuarios (carga desde Excel)"""
    if request.method == 'POST':
        form = UserDataUploadForm(request.POST, request.FILES)
        if form.is_valid():
            voting_id = form.cleaned_data.get('voting_id')
            excel_file = request.FILES.get('file')
            
            try:
                voting = Voting.objects.get(id=voting_id)
                count_imported = ExcelService.import_user_data(voting, excel_file)
                messages.success(request, f"{count_imported} usuarios importados correctamente.")
                return redirect('dashboard:user_data_management')
            except Voting.DoesNotExist:
                messages.error(request, "Votación no encontrada.")
            except Exception as e:
                messages.error(request, f"Error al importar: {str(e)}")
    else:
        form = UserDataUploadForm()
    
    votings = Voting.objects.all()
    
    context = {
        'form': form,
        'votings': votings,
    }
    return render(request, 'dashboard/user_data_management.html', context)


@maintainer_login_required
def voting_statistics(request, voting_id):
    """Vista de estadísticas detalladas de una votación"""
    voting = get_object_or_404(Voting, id=voting_id)
    subjects = voting.subjects.all()
    
    stats = []
    total_votes = VotingRecord.objects.filter(id_voting=voting).count()
    
    for subject in subjects:
        count = Count.objects.filter(id_subject=subject).first()
        votes = count.number if count else 0
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
        
        stats.append({
            'subject': subject,
            'votes': votes,
            'percentage': round(percentage, 2),
        })
    
    # Preparar datos para gráfico
    chart_data = {
        'labels': [s['subject'].name for s in stats],
        'data': [s['votes'] for s in stats],
    }
    chart_json = json.dumps(chart_data)
    
    context = {
        'voting': voting,
        'stats': stats,
        'total_votes': total_votes,
        'chart_json': chart_json,
    }
    return render(request, 'dashboard/voting_statistics.html', context)


@maintainer_login_required
def generate_report(request, voting_id):
    """Vista para generar reportes de votaciones"""
    voting = get_object_or_404(Voting, id=voting_id)
    
    records = VotingRecord.objects.filter(id_voting=voting).select_related(
        'id_subject', 'user_data'
    ).order_by('-voted_at')
    
    context = {
        'voting': voting,
        'records': records,
    }
    return render(request, 'dashboard/report.html', context)


@maintainer_login_required
def maintainers_management(request):
    """Vista para gestionar maintainers"""
    maintainers = Maintainer.objects.all().order_by('-created_at')
    roles = Role.objects.all()
    
    context = {
        'maintainers': maintainers,
        'roles': roles,
    }
    return render(request, 'dashboard/maintainers_management.html', context)
