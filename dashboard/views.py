from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.http import require_http_methods
from django.db import connection, transaction
from django.db.models import Sum, Count as DbCount, Q
from django.utils import timezone
from voting.models import Maintainer, Voting, Subject, UserData, VotingRecord, Count, Role, PasswordResetToken, Militante
from dashboard.forms import MaintainerLoginForm, VotingForm, SubjectForm, UserDataUploadForm, MaintainerEditForm, MaintainerCreateForm, MilitanteInviteForm
from dashboard.decorators import maintainer_login_required, admin_required, no_auditor
from dashboard.services import ExcelService
from voting.services import EmailService
from voting.time_utils import get_real_now
from datetime import timedelta
import json
import logging
import secrets
import hmac

logger = logging.getLogger(__name__)

DELETE_VOTING_TOKEN_KEY = 'delete_voting_token'
DELETE_VOTING_TOKEN_EXPIRES_KEY = 'delete_voting_token_expires_at'
DELETE_VOTING_TOKEN_TTL_HOURS = 12


def _expire_delete_token_and_logout(request):
    """Cierra sesión si el token de eliminación expiró."""
    request.session.flush()
    messages.error(request, "Tu token de eliminación expiró. Inicia sesión nuevamente.")
    return redirect('dashboard:login')


def _get_or_create_delete_voting_token(request):
    """
    Entrega token de eliminación válido por sesión.
    Si está expirado, fuerza cierre de sesión.
    """
    token = request.session.get(DELETE_VOTING_TOKEN_KEY)
    expires_at = request.session.get(DELETE_VOTING_TOKEN_EXPIRES_KEY)
    now_ts = timezone.now().timestamp()

    if token and expires_at:
        if now_ts <= float(expires_at):
            return token, None
        return None, _expire_delete_token_and_logout(request)

    new_token = secrets.token_urlsafe(32)
    new_expires = (timezone.now() + timedelta(hours=DELETE_VOTING_TOKEN_TTL_HOURS)).timestamp()
    request.session[DELETE_VOTING_TOKEN_KEY] = new_token
    request.session[DELETE_VOTING_TOKEN_EXPIRES_KEY] = new_expires
    request.session.modified = True
    return new_token, None


def _validate_delete_voting_token(request):
    """Valida token de eliminación recibido por formulario."""
    session_token = request.session.get(DELETE_VOTING_TOKEN_KEY)
    expires_at = request.session.get(DELETE_VOTING_TOKEN_EXPIRES_KEY)
    form_token = request.POST.get('delete_voting_token', '')
    now_ts = timezone.now().timestamp()

    if not session_token or not expires_at:
        return False, "Falta token de seguridad para eliminar."

    if now_ts > float(expires_at):
        return False, _expire_delete_token_and_logout(request)

    if not form_token or not hmac.compare_digest(str(session_token), str(form_token)):
        return False, "Token de seguridad inválido para eliminar."

    return True, None


def _with_authorized_votingrecord_delete(callback):
    """
    Ejecuta una operación de borrado autorizando temporalmente DELETE en VotingRecord
    solo para esta sesión SQL (MySQL/MariaDB).
    """
    if connection.vendor != 'mysql':
        return callback()

    with connection.cursor() as cursor:
        cursor.execute("SET @allow_votingrecord_delete = 1")
    try:
        return callback()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SET @allow_votingrecord_delete = 0")


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
                # Verificar contraseña usando check_password de Django
                if check_password(password, maintainer.password):
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
    # Verificar si es auditor
    maintainer_id = request.session.get('maintainer_id')
    maintainer = Maintainer.objects.get(id=maintainer_id)
    is_auditor = maintainer.id_role.name.lower() == 'auditor'
    
    if is_auditor:
        # Vista limitada para auditores
        from django.db.models import Count as DbCount
        votings = Voting.objects.select_related('id_region').annotate(
            vote_count=DbCount('votingrecord')
        ).order_by('-start_date')
        total_votes = VotingRecord.objects.count()
        
        context = {
            'votings': votings,
            'total_votes': total_votes,
            'now': get_real_now(),
        }
        return render(request, 'dashboard/auditor_dashboard.html', context)
    
    # Vista completa para administradores
    total_votings = Voting.objects.count()
    active_votings = Voting.objects.filter(
        start_date__lte=get_real_now(),
        finish_date__gte=get_real_now()
    ).count()
    total_votes = VotingRecord.objects.count()
    
    context = {
        'total_votings': total_votings,
        'active_votings': active_votings,
        'total_votes': total_votes,
    }
    return render(request, 'dashboard/dashboard.html', context)


@maintainer_login_required
@no_auditor
def votings_management(request):
    """Vista para gestionar votaciones"""
    votings = Voting.objects.all().order_by('-created_at')
    now = get_real_now()
    
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
        'now': now,
    }
    return render(request, 'dashboard/votings_management.html', context)


@maintainer_login_required
@no_auditor
def voting_detail(request, voting_id):
    """Vista de detalle de una votación en el dashboard"""
    voting = get_object_or_404(Voting, id=voting_id)
    subjects = voting.subjects.all()
    
    # Verificar si el usuario es administrador
    maintainer_id = request.session.get('maintainer_id')
    maintainer = Maintainer.objects.get(id=maintainer_id) if maintainer_id else None
    is_admin = maintainer and maintainer.id_role.name.lower() == 'administrador' or maintainer.id_role.name.lower() == 'admin'
    
    stats = []
    total_votes = 0
    
    for subject in subjects:
        votes = VotingRecord.objects.filter(id_subject=subject).count()
        total_votes += votes
        stats.append({
            'subject': subject,
            'votes': votes,
        })

    delete_voting_token = None
    if is_admin:
        delete_voting_token, logout_redirect = _get_or_create_delete_voting_token(request)
        if logout_redirect:
            return logout_redirect
    
    context = {
        'voting': voting,
        'subjects': subjects,
        'stats': stats,
        'total_votes': total_votes,
        'is_admin': is_admin,
        'delete_voting_token': delete_voting_token,
    }
    return render(request, 'dashboard/voting_detail.html', context)


@maintainer_login_required
@no_auditor
def subjects_management(request, voting_id):
    """Vista para gestionar subjects de una votación"""
    voting = get_object_or_404(Voting, id=voting_id)
    subjects = voting.subjects.all()
    
    if request.method == 'POST':
        if voting.is_open():
            messages.error(request, "No se pueden agregar candidatos mientras la votación está en período activo.")
            return redirect('dashboard:subjects_management', voting_id=voting_id)
        
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
@no_auditor
def user_data_management(request):
    """Vista principal de gestión de usuarios - muestra opciones"""
    return render(request, 'dashboard/user_data_management.html')


@maintainer_login_required
@no_auditor
def user_data_upload(request):
    """Vista para cargar datos de usuarios desde Excel"""
    if request.method == 'POST':
        form = UserDataUploadForm(request.POST, request.FILES)
        if form.is_valid():
            voting_id = form.cleaned_data.get('voting_id')
            excel_file = request.FILES.get('file')
            
            try:
                voting = Voting.objects.get(id=voting_id)
                count_imported = ExcelService.import_user_data(voting, excel_file)
                
                # Obtener RUTs importados y buscar militantes para notificar
                imported_ruts = UserData.objects.filter(id_voting=voting).values_list('rut', flat=True)
                militantes_to_notify = list(Militante.objects.filter(rut__in=imported_ruts, is_active=True))
                
                email_results = {'sent': 0, 'failed': 0}
                if militantes_to_notify:
                    email_results = EmailService.send_bulk_upcoming_voting_emails(militantes_to_notify, voting)
                
                msg = f"{count_imported} usuarios importados correctamente."
                if email_results['sent'] > 0:
                    msg += f" {email_results['sent']} correos de notificación enviados."
                if email_results['failed'] > 0:
                    msg += f" {email_results['failed']} correos fallidos."
                messages.success(request, msg)
                return redirect('dashboard:user_data_upload')
            except Voting.DoesNotExist:
                messages.error(request, "Votación no encontrada.")
            except Exception as e:
                messages.error(request, f"Error al importar: {str(e)}")
    else:
        form = UserDataUploadForm()
    
    context = {
        'form': form,
    }
    return render(request, 'dashboard/user_data_upload.html', context)


@maintainer_login_required
@no_auditor
def militante_invite(request):
    """Vista para enviar invitaciones de registro a militantes desde Excel"""
    if request.method == 'POST':
        form = MilitanteInviteForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES.get('file')
            
            try:
                # Importar datos del Excel
                users_data = ExcelService.import_militantes_from_excel(excel_file)
                
                if not users_data:
                    messages.warning(request, "No se encontraron usuarios válidos para invitar.")
                    return redirect('dashboard:militante_invite')
                
                # Obtener URL base
                base_url = request.build_absolute_uri('/')[:-1]  # Quitar trailing slash
                
                # Enviar correos con delay
                results = EmailService.send_bulk_registration_emails(users_data, base_url)
                
                messages.success(
                    request, 
                    f"Proceso completado: {results['sent']} correos enviados, {results['failed']} fallidos."
                )
                
                if results['errors']:
                    for error in results['errors'][:5]:  # Mostrar máximo 5 errores
                        messages.warning(request, error)
                
                return redirect('dashboard:militante_invite')
                
            except Exception as e:
                messages.error(request, f"Error al procesar: {str(e)}")
    else:
        form = MilitanteInviteForm()
    
    context = {
        'form': form,
    }
    return render(request, 'dashboard/militante_invite.html', context)


@maintainer_login_required
@no_auditor
def voting_statistics(request, voting_id):
    """Vista de estadísticas detalladas de una votación"""
    voting = get_object_or_404(Voting, id=voting_id)

    # Solo permitir acceso si la votación ya finalizó (hora chilena)
    import pytz
    santiago_tz = pytz.timezone('America/Santiago')
    now_chile = get_real_now()
    finish_date_chile = voting.finish_date.astimezone(santiago_tz)
    if finish_date_chile >= now_chile:
        messages.error(request, 'Las estadísticas solo están disponibles una vez finalizada la votación.')
        return redirect('dashboard:votings_management')

    subjects = voting.subjects.all()
    
    # Contar total de RUTs registrados y votos realizados
    total_registered = UserData.objects.filter(id_voting=voting).count()
    total_votes = VotingRecord.objects.filter(id_voting=voting).count()
    no_votes = total_registered - total_votes
    
    stats = []
    for subject in subjects:
        votes = VotingRecord.objects.filter(id_subject=subject).count()
        percentage = (votes / total_votes) if total_votes > 0 else 0
        final_percentage = round(percentage * 100, 2)
        
        stats.append({
            'subject': subject,
            'votes': votes,
            'percentage': final_percentage,
        })
    
    # Agregar opción "No Voto"
    no_vote_percentage = (no_votes / total_registered) if total_registered > 0 else 0
    no_final_percentage = round(no_vote_percentage * 100, 2)
    stats.append({
        'subject': type('obj', (object,), {'name': 'No Voto'})(),
        'votes': no_votes,
        'percentage': no_final_percentage,
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
        'total_registered': total_registered,
        'chart_json': chart_json,
    }
    return render(request, 'dashboard/voting_statistics.html', context)


@maintainer_login_required
@no_auditor
def generate_report(request, voting_id):
    """Vista para generar reportes de votaciones (solo estadísticas)"""
    voting = get_object_or_404(Voting, id=voting_id)

    # Solo permitir acceso si la votación ya finalizó (hora chilena)
    import pytz
    santiago_tz = pytz.timezone('America/Santiago')
    now_chile = get_real_now()
    finish_date_chile = voting.finish_date.astimezone(santiago_tz)
    if finish_date_chile >= now_chile:
        messages.error(request, 'El reporte solo está disponible una vez finalizada la votación.')
        return redirect('dashboard:votings_management')

    subjects = voting.subjects.all()
    
    # Contar total de RUTs registrados y votos realizados
    total_registered = UserData.objects.filter(id_voting=voting).count()
    total_votes = VotingRecord.objects.filter(id_voting=voting).count()
    no_votes = total_registered - total_votes
    
    stats = []
    
    include_no_voto = request.GET.get('include_no_voto', 'true') == 'true'
    base_total = total_registered if include_no_voto else total_votes

    for subject in subjects:
        votes = VotingRecord.objects.filter(id_subject=subject).count()
        percentage = (votes / base_total) if base_total > 0 else 0
        
        stats.append({
            'subject': subject,
            'votes': votes,
            'percentage': round(percentage * 100, 2),
        })
    
    # Agregar opción "No Voto"
    if include_no_voto:
        no_vote_percentage = (no_votes / base_total) if base_total > 0 else 0
        stats.append({
            'subject': type('obj', (object,), {'name': 'No Voto'})(),
            'votes': no_votes,
            'percentage': round(no_vote_percentage * 100, 2),
        })
    
    context = {
        'voting': voting,
        'stats': stats,
        'total_votes': total_votes,
        'total_registered': total_registered,
    }
    return render(request, 'dashboard/report.html', context)


@maintainer_login_required
@no_auditor
def maintainers_management(request):
    """Vista para gestionar maintainers"""
    maintainers = Maintainer.objects.all().order_by('-created_at')
    roles = Role.objects.all()
    
    # Verificar si el usuario es administrador
    maintainer_id = request.session.get('maintainer_id')
    maintainer = Maintainer.objects.get(id=maintainer_id) if maintainer_id else None
    is_admin = maintainer and maintainer.id_role.name.lower() == 'administrador' or maintainer.id_role.name.lower() == 'admin'
    
    context = {
        'maintainers': maintainers,
        'roles': roles,
        'is_admin': is_admin,
    }
    return render(request, 'dashboard/maintainers_management.html', context)


@admin_required
def create_maintainer(request):
    """Vista para crear un nuevo administrador (solo admins)"""
    if request.method == 'POST':
        form = MaintainerCreateForm(request.POST)
        if form.is_valid():
            maintainer = form.save()
            messages.success(request, f"Maintainer '{maintainer.name} {maintainer.lastname}' creado correctamente.")
            return redirect('dashboard:maintainers_management')
    else:
        form = MaintainerCreateForm()
    
    context = {
        'form': form,
        'page_title': 'Crear Nuevo Administrador',
    }
    return render(request, 'dashboard/create_maintainer.html', context)


@admin_required
def edit_maintainer(request, maintainer_id):
    """Vista para editar administrador"""
    maintainer = get_object_or_404(Maintainer, id=maintainer_id)
    
    if request.method == 'POST':
        form = MaintainerEditForm(request.POST, instance=maintainer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Administrador '{maintainer.name}' actualizado correctamente.")
            return redirect('dashboard:maintainers_management')
    else:
        form = MaintainerEditForm(instance=maintainer)
    
    context = {
        'form': form,
        'maintainer': maintainer,
    }
    return render(request, 'dashboard/edit_maintainer.html', context)


@admin_required
@require_http_methods(["POST"])
def send_password_reset_email(request, maintainer_id):
    """Vista para enviar email de restablecimiento de contraseña"""
    maintainer = get_object_or_404(Maintainer, id=maintainer_id)
    
    try:
        # Crear token de recuperación
        reset_token = PasswordResetToken.create_token(maintainer)
        
        # Generar link de recuperación en dashboard (sin login requerido)
        reset_link = request.build_absolute_uri(f'/dashboard/reset-password/{reset_token.token}/')
        
        EmailService.send_password_reset_email(
            to_email=maintainer.mail,
            user_name=f"{maintainer.name} {maintainer.lastname}",
            reset_link=reset_link
        )
        logger.info(f"Email de restablecimiento enviado para maintainer_id={maintainer_id}")
        
        messages.success(request, f"Email de restablecimiento enviado a {maintainer.mail}")
    except Exception as e:
        logger.error("Error al enviar email de restablecimiento")
        messages.error(request, "Error al enviar el email de restablecimiento.")
    
    return redirect('dashboard:edit_maintainer', maintainer_id=maintainer_id)


@admin_required
@require_http_methods(["POST"])
def delete_maintainer(request, maintainer_id):
    """Vista para eliminar un maintainer (solo admins)"""
    maintainer = get_object_or_404(Maintainer, id=maintainer_id)
    maintainer_name = f"{maintainer.name} {maintainer.lastname}"
    
    # No permitir que se elimine a sí mismo
    if maintainer.id == request.session.get('maintainer_id'):
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect('dashboard:maintainers_management')
    
    # Eliminar completamente el maintainer
    maintainer.delete()
    
    messages.success(request, f"Maintainer '{maintainer_name}' eliminado correctamente.")
    return redirect('dashboard:maintainers_management')


@admin_required
@require_http_methods(["POST"])
def delete_voting(request, voting_id):
    """Vista para eliminar una votación completa (solo admins)"""
    voting = get_object_or_404(Voting, id=voting_id)
    
    if voting.is_open():
        messages.error(request, "No se puede eliminar una votación mientras está en período activo.")
        return redirect('dashboard:voting_detail', voting_id=voting_id)

    token_ok, token_result = _validate_delete_voting_token(request)
    if not token_ok:
        if hasattr(token_result, 'status_code'):
            return token_result
        messages.error(request, token_result)
        return redirect('dashboard:voting_detail', voting_id=voting_id)

    voting_title = voting.title
    
    try:
        # Eliminar todos los registros asociados en cascada con autorización temporal DB
        with transaction.atomic():
            _with_authorized_votingrecord_delete(voting.delete)
        messages.success(request, f"Votación '{voting_title}' y todos sus datos han sido eliminados correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar la votación: {str(e)}")
    
    return redirect('dashboard:votings_management')

def reset_password(request, token):
    """Vista pública para cambiar la contraseña usando un token válido (SIN LOGIN REQUERIDO)"""
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, "El link de recuperación es inválido o ha expirado.")
        return redirect('dashboard:login')
    
    # Validar que el token sea válido
    if not reset_token.is_valid():
        messages.error(request, "El link de recuperación ha expirado. Solicita uno nuevo.")
        return redirect('dashboard:login')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        if not password or len(password) < 6:
            messages.error(request, "La contraseña debe tener al menos 6 caracteres.")
            return render(request, 'dashboard/reset_password.html', {'token': token})
        
        if password != password_confirm:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'dashboard/reset_password.html', {'token': token})
        
        # Actualizar contraseña
        maintainer = reset_token.maintainer
        maintainer.password = make_password(password)
        maintainer.save()
        
        # Marcar token como usado
        reset_token.used = True
        reset_token.save()
        
        messages.success(request, "Tu contraseña ha sido actualizada correctamente. Inicia sesión.")
        return redirect('dashboard:login')
    
    return render(request, 'dashboard/reset_password.html', {'token': token})


def request_password_reset(request):
    """Vista pública para solicitar un reset de contraseña (SIN LOGIN REQUERIDO)"""
    if request.method == 'POST':
        mail = request.POST.get('mail', '').strip()
        
        try:
            maintainer = Maintainer.objects.get(mail=mail, is_active=True)
            # Crear token de recuperación
            reset_token = PasswordResetToken.create_token(maintainer)
            
            # Enviar email con link de recuperación
            reset_link = request.build_absolute_uri(f'/dashboard/reset-password/{reset_token.token}/')
            EmailService.send_password_reset_email(
                to_email=maintainer.mail,
                user_name=maintainer.name,
                reset_link=reset_link
            )
            
            messages.success(request, f"Se ha enviado un link de recuperación a {mail}. Revisa tu bandeja de entrada.")
        except Maintainer.DoesNotExist:
            # No revelar si el email existe o no por seguridad
            messages.info(request, "Si el correo existe, recibirás un email con instrucciones.")
        
        return redirect('dashboard:request_password_reset')
    
    return render(request, 'dashboard/request_password_reset.html')
