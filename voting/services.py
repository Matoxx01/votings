from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.utils import timezone
import time


class EmailService:
    """Servicio para enviar correos electrónicos"""

    @staticmethod
    def send_confirmation_email(to_email, user_name, voting_title):
        """
        Envía un correo de confirmación de voto
        
        Args:
            to_email: Correo del votante
            user_name: Nombre del votante
            voting_title: Título de la votación
        """
        subject = f"Confirmación de Voto - {voting_title}"
        
        context = {
            'user_name': user_name,
            'voting_title': voting_title,
        }
        
        html_message = render_to_string('voting/emails/confirmation_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_voting_reminder_email(to_email, user_name, voting_title):
        """
        Envía un correo recordatorio para votar
        
        Args:
            to_email: Correo del votante
            user_name: Nombre del votante
            voting_title: Título de la votación
        """
        subject = f"Recordatorio: Votación en curso - {voting_title}"
        
        context = {
            'user_name': user_name,
            'voting_title': voting_title,
        }
        
        html_message = render_to_string('voting/emails/reminder_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_password_reset_email(to_email, user_name, reset_link):
        """
        Envía un correo para restablecimiento de contraseña
        
        Args:
            to_email: Correo del administrador
            user_name: Nombre del administrador
            reset_link: Enlace para resetear contraseña
        """
        subject = "Restablecimiento de Contraseña - Sistema de Votaciones"
        
        context = {
            'user_name': user_name,
            'reset_link': reset_link,
        }
        
        html_message = render_to_string('voting/emails/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_militante_welcome_email(to_email, nombre):
        """
        Envía un correo de bienvenida confirmando el registro exitoso del militante
        
        Args:
            to_email: Correo del militante
            nombre: Nombre del militante
        """
        subject = "¡Registro Completado Exitosamente! - Sistema de Votaciones"
        
        context = {
            'nombre': nombre,
        }
        
        html_message = render_to_string('voting/emails/militante_welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_militante_registration_email(to_email, nombre, registration_link):
        """
        Envía un correo de invitación para registro de militante
        
        Args:
            to_email: Correo del militante
            nombre: Nombre del militante
            registration_link: Enlace para registrarse
        """
        subject = "Invitación para Registro - Sistema de Votaciones"
        
        context = {
            'nombre': nombre,
            'registration_link': registration_link,
        }
        
        html_message = render_to_string('voting/emails/militante_registration_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_militante_password_reset_email(to_email, nombre, reset_link):
        """
        Envía un correo para restablecimiento de contraseña de militante
        
        Args:
            to_email: Correo del militante
            nombre: Nombre del militante
            reset_link: Enlace para resetear contraseña
        """
        subject = "Restablecimiento de Contraseña - Sistema de Votaciones"
        
        context = {
            'nombre': nombre,
            'reset_link': reset_link,
        }
        
        html_message = render_to_string('voting/emails/militante_password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_verification_code_email(to_email, code):
        """
        Envía un código de 6 dígitos para verificar el correo
        """
        subject = "Código de Verificación - Cambio de Correo"
        
        context = {
            'verification_code': code,
        }
        
        html_message = render_to_string('voting/emails/verification_code_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_upcoming_voting_email(to_email, nombre, voting_title, voting_description, start_date, finish_date, candidates=None):
        """
        Envía un correo notificando una votación próxima
        """
        subject = f"Votación Próxima - {voting_title}"
        
        context = {
            'nombre': nombre,
            'voting_title': voting_title,
            'voting_description': voting_description,
            'start_date': start_date,
            'finish_date': finish_date,
            'candidates': candidates,
        }
        
        html_message = render_to_string('voting/emails/upcoming_voting_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_upcoming_voting_with_registration_email(to_email, nombre, voting_title, voting_description, start_date, finish_date, registration_link, candidates=None):
        """
        Envía un correo notificando una votación próxima e invita a registrarse
        """
        subject = f"Próxima Votación y Registro - {voting_title}"
        
        context = {
            'nombre': nombre,
            'voting_title': voting_title,
            'voting_description': voting_description,
            'start_date': start_date,
            'finish_date': finish_date,
            'registration_link': registration_link,
            'candidates': candidates,
        }
        
        html_message = render_to_string('voting/emails/upcoming_voting_with_registration_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def send_bulk_upcoming_voting_emails(militantes, voting, delay=0.2):
        """
        Envía correos masivos notificando una votación próxima
        
        Args:
            militantes: QuerySet de Militante
            voting: Instancia de Voting
            delay: Segundos entre cada envío
            
        Returns:
            dict: {sent: int, failed: int, errors: list}
        """
        results = {'sent': 0, 'failed': 0, 'errors': []}
        
        start_date = voting.start_date.strftime('%d/%m/%Y %H:%M')
        finish_date = voting.finish_date.strftime('%d/%m/%Y %H:%M')
        
        # Obtener candidatos para la votación
        candidates = voting.subjects.all()
        
        for i, militante in enumerate(militantes):
            try:
                EmailService.send_upcoming_voting_email(
                    to_email=militante.mail,
                    nombre=militante.nombre,
                    voting_title=voting.title,
                    voting_description=voting.description,
                    start_date=start_date,
                    finish_date=finish_date,
                    candidates=candidates,
                )
                
                results['sent'] += 1
                
                if i < len(militantes) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{militante.mail}: {str(e)}")
        
        return results

    @staticmethod
    def send_bulk_upcoming_voting_emails_for_unregistered(tokens, voting, base_url, delay=0.2):
        """
        Envía correos masivos notificando una votación a usuarios pendientes de registro
        """
        results = {'sent': 0, 'failed': 0, 'errors': []}
        
        start_date = voting.start_date.strftime('%d/%m/%Y %H:%M')
        finish_date = voting.finish_date.strftime('%d/%m/%Y %H:%M')
        
        candidates = voting.subjects.all()
        
        for i, token_obj in enumerate(tokens):
            try:
                registration_link = f"{base_url}/registro-militante/{token_obj.token}/"
                
                EmailService.send_upcoming_voting_with_registration_email(
                    to_email=token_obj.mail,
                    nombre=token_obj.nombre,
                    voting_title=voting.title,
                    voting_description=voting.description,
                    start_date=start_date,
                    finish_date=finish_date,
                    registration_link=registration_link,
                    candidates=candidates,
                )
                
                results['sent'] += 1
                
                if i < len(tokens) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{token_obj.mail}: {str(e)}")
        
        return results

    @staticmethod
    def send_bulk_registration_emails(users_data, base_url, delay=0.2):
        """
        Envía correos de registro masivamente con delay
        
        Args:
            users_data: Lista de diccionarios con {nombre, rut, mail, token}
            base_url: URL base del sitio
            delay: Segundos entre cada envío (default 0.2)
            
        Returns:
            dict: {sent: int, failed: int, errors: list}
        """
        from voting.models import MilitanteRegistrationToken
        
        results = {'sent': 0, 'failed': 0, 'errors': []}
        
        for i, user in enumerate(users_data):
            try:
                # Crear token de registro
                token_obj = MilitanteRegistrationToken.create_token(
                    nombre=user['nombre'],
                    rut=user['rut'],
                    mail=user['mail']
                )
                
                registration_link = f"{base_url}/registro-militante/{token_obj.token}/"
                
                EmailService.send_militante_registration_email(
                    to_email=user['mail'],
                    nombre=user['nombre'],
                    registration_link=registration_link
                )
                
                results['sent'] += 1
                
                # Delay entre correos (excepto el último)
                if i < len(users_data) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{user['mail']}: {str(e)}")
        
        return results


class EmailQueueService:
    """Servicio para gestionar la cola de correos en base de datos"""

    @staticmethod
    def queue_upcoming_voting_emails(militantes, voting, upload_log):
        from voting.models import EmailQueueItem
        items = []
        for militante in militantes:
            items.append(EmailQueueItem(
                upload_log=upload_log,
                email_type='UPCOMING_VOTING',
                status='PENDING',
                recipient_email=militante.mail,
                recipient_name=militante.nombre,
                voting=voting,
            ))
        EmailQueueItem.objects.bulk_create(items)

    @staticmethod
    def queue_upcoming_voting_emails_for_unregistered(tokens, voting, base_url, upload_log):
        from voting.models import EmailQueueItem
        items = []
        for token_obj in tokens:
            items.append(EmailQueueItem(
                upload_log=upload_log,
                email_type='UPCOMING_VOTING_UNREGISTERED',
                status='PENDING',
                recipient_email=token_obj.mail,
                recipient_name=token_obj.nombre,
                voting=voting,
                base_url=base_url,
                token_obj=token_obj,
            ))
        EmailQueueItem.objects.bulk_create(items)

    @staticmethod
    def queue_registration_emails(users_data, base_url, upload_log):
        from voting.models import EmailQueueItem, MilitanteRegistrationToken
        items = []
        for user in users_data:
            # Crear token de registro si no existe o usar uno nuevo
            token_obj = MilitanteRegistrationToken.create_token(
                nombre=user['nombre'],
                rut=user['rut'],
                mail=user['mail']
            )
            items.append(EmailQueueItem(
                upload_log=upload_log,
                email_type='REGISTRO_MILITANTE',
                status='PENDING',
                recipient_email=user['mail'],
                recipient_name=user['nombre'],
                base_url=base_url,
                token_obj=token_obj,
            ))
        EmailQueueItem.objects.bulk_create(items)

    @staticmethod
    def process_queue_for_log(log_id, delay=0.2):
        from voting.models import DataUploadLog, EmailQueueItem
        from django.db import close_old_connections
        close_old_connections()
        try:
            upload_log = DataUploadLog.objects.get(id=log_id)
            # Marcar in_progress True si no lo estaba
            if not upload_log.details.get('in_progress'):
                upload_log.details['in_progress'] = True
                upload_log.save()

            items = EmailQueueItem.objects.filter(upload_log=upload_log, status__in=['PENDING', 'PROCESSING']).order_by('created_at')
            
            for item in items:
                item.status = 'PROCESSING'
                item.save()
                
                try:
                    if item.email_type == 'UPCOMING_VOTING':
                        voting = item.voting
                        start_date = voting.start_date.strftime('%d/%m/%Y %H:%M')
                        finish_date = voting.finish_date.strftime('%d/%m/%Y %H:%M')
                        candidates = voting.subjects.all()
                        
                        EmailService.send_upcoming_voting_email(
                            to_email=item.recipient_email,
                            nombre=item.recipient_name,
                            voting_title=voting.title,
                            voting_description=voting.description,
                            start_date=start_date,
                            finish_date=finish_date,
                            candidates=candidates,
                        )
                        
                    elif item.email_type == 'UPCOMING_VOTING_UNREGISTERED':
                        voting = item.voting
                        start_date = voting.start_date.strftime('%d/%m/%Y %H:%M')
                        finish_date = voting.finish_date.strftime('%d/%m/%Y %H:%M')
                        candidates = voting.subjects.all()
                        registration_link = f"{item.base_url}/registro-militante/{item.token_obj.token}/"
                        
                        EmailService.send_upcoming_voting_with_registration_email(
                            to_email=item.recipient_email,
                            nombre=item.recipient_name,
                            voting_title=voting.title,
                            voting_description=voting.description,
                            start_date=start_date,
                            finish_date=finish_date,
                            registration_link=registration_link,
                            candidates=candidates,
                        )
                        
                    elif item.email_type == 'REGISTRO_MILITANTE':
                        registration_link = f"{item.base_url}/registro-militante/{item.token_obj.token}/"
                        
                        EmailService.send_militante_registration_email(
                            to_email=item.recipient_email,
                            nombre=item.recipient_name,
                            registration_link=registration_link
                        )

                    item.status = 'SENT'
                    item.save()
                    
                    upload_log.emails_sent += 1
                    upload_log.save()
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    item.status = 'FAILED'
                    item.error_message = str(e)
                    item.save()
                    
                    upload_log.emails_failed += 1
                    errors = upload_log.details.get('email_errors', [])
                    errors.append(f"{item.recipient_email}: {str(e)}")
                    upload_log.details['email_errors'] = errors
                    upload_log.save()

            # Finalizar log si ya no quedan items pendientes
            pendientes = EmailQueueItem.objects.filter(upload_log=upload_log, status__in=['PENDING', 'PROCESSING']).exists()
            if not pendientes:
                upload_log.details['in_progress'] = False
                upload_log.save()
        except Exception as e:
            try:
                upload_log = DataUploadLog.objects.get(id=log_id)
                upload_log.details['in_progress'] = False
                upload_log.details['process_error'] = str(e)
                upload_log.save()
            except Exception:
                pass
        finally:
            close_old_connections()

    @staticmethod
    def resume_all_pending_queues():
        import threading
        from voting.models import DataUploadLog, EmailQueueItem
        from django.db import close_old_connections
        close_old_connections()
        try:
            # Buscar logs con in_progress True
            logs_in_progress = DataUploadLog.objects.filter(details__in_progress=True)
            for log in logs_in_progress:
                # Revertir items PROCESSING a PENDING por el reinicio
                EmailQueueItem.objects.filter(upload_log=log, status='PROCESSING').update(status='PENDING')
                
                # Iniciar hilo de procesamiento
                thread = threading.Thread(
                    target=EmailQueueService.process_queue_for_log,
                    args=(log.id,)
                )
                thread.daemon = True
                thread.start()
        except Exception:
            pass
        finally:
            close_old_connections()
