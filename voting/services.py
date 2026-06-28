from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.utils import timezone
import time
import pytz
import os
import json
import urllib.request


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
        
        santiago_tz = pytz.timezone('America/Santiago')
        start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
        finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
        
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
        
        santiago_tz = pytz.timezone('America/Santiago')
        start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
        finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
        
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

    @staticmethod
    def get_upcoming_voting_email_data(to_email, nombre, voting_title, voting_description, start_date, finish_date, candidates=None):
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
        return {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to_email],
            'subject': subject,
            'html': html_message,
            'text': plain_message,
        }

    @staticmethod
    def get_upcoming_voting_with_registration_email_data(to_email, nombre, voting_title, voting_description, start_date, finish_date, registration_link, candidates=None):
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
        return {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to_email],
            'subject': subject,
            'html': html_message,
            'text': plain_message,
        }

    @staticmethod
    def get_militante_registration_email_data(to_email, nombre, registration_link):
        subject = "Invitación para Registro - Sistema de Votaciones"
        context = {
            'nombre': nombre,
            'registration_link': registration_link,
        }
        html_message = render_to_string('voting/emails/militante_registration_email.html', context)
        plain_message = strip_tags(html_message)
        return {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to_email],
            'subject': subject,
            'html': html_message,
            'text': plain_message,
        }

    @staticmethod
    def get_voting_reminder_email_data(to_email, user_name, voting_title):
        subject = f"Recordatorio: Votación en curso - {voting_title}"
        context = {
            'user_name': user_name,
            'voting_title': voting_title,
        }
        html_message = render_to_string('voting/emails/reminder_email.html', context)
        plain_message = strip_tags(html_message)
        return {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [to_email],
            'subject': subject,
            'html': html_message,
            'text': plain_message,
        }

    @staticmethod
    def send_resend_batch(batch_payload):
        """
        Envía un lote de correos utilizando la API Batch de Resend.
        Retorna True si el envío fue exitoso, o False si falló (para activar fallback).
        """
        api_key = os.getenv('RESEND_API_KEY', getattr(settings, 'EMAIL_HOST_PASSWORD', ''))
        if not api_key:
            return False
            
        url = "https://api.resend.com/emails/batch"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = json.dumps(batch_payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                if response.status in [200, 201]:
                    return True
                return False
        except Exception:
            return False


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
    def queue_voting_reminder_emails(militantes, voting, upload_log):
        from voting.models import EmailQueueItem
        items = []
        for militante in militantes:
            items.append(EmailQueueItem(
                upload_log=upload_log,
                email_type='VOTING_REMINDER',
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
        """
        Procesa la cola de correos para un log específico.
        
        PROTECCIONES CONTRA ENVÍOS DUPLICADOS:
        1. select_for_update(skip_locked=True): si otro hilo/worker ya tomó un item, se salta
        2. transaction.atomic(): la selección y el marcado PROCESSING son una operación indivisible
        3. Solo toma items PENDING, nunca resetea PROCESSING
        4. email_errors limitado a 50 entradas para evitar JSON gigante (Error 500/1038)
        """
        from voting.models import DataUploadLog, EmailQueueItem
        from django.db import close_old_connections, transaction
        close_old_connections()
        try:
            upload_log = DataUploadLog.objects.get(id=log_id)
            if not upload_log.details.get('in_progress'):
                upload_log.details['in_progress'] = True
                upload_log.save()

            santiago_tz = pytz.timezone('America/Santiago')

            while True:
                # === FASE 1: Reclamar un lote de forma ATÓMICA ===
                # select_for_update(skip_locked=True) garantiza que si otro hilo
                # ya bloqueó estos items, este hilo los salta en vez de esperar.
                # Ordenar por 'id' (no 'created_at') para evitar MySQL Error 1038.
                with transaction.atomic():
                    batch_items = list(
                        EmailQueueItem.objects
                        .select_for_update(skip_locked=True)
                        .filter(upload_log_id=log_id, status='PENDING')
                        .order_by('id')[:100]
                    )
                    if not batch_items:
                        break  # No quedan items pendientes, salir del loop
                    
                    # Marcar como PROCESSING dentro de la misma transacción atómica
                    EmailQueueItem.objects.filter(
                        id__in=[item.id for item in batch_items]
                    ).update(status='PROCESSING')

                # === FASE 2: Construir payload para Resend Batch API ===
                batch_payload = []
                item_data_map = {}

                for item in batch_items:
                    try:
                        if item.email_type == 'UPCOMING_VOTING':
                            voting = item.voting
                            start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                            finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                            candidates = voting.subjects.all()
                            email_data = EmailService.get_upcoming_voting_email_data(
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
                            start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                            finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                            candidates = voting.subjects.all()
                            registration_link = f"{item.base_url}/registro-militante/{item.token_obj.token}/"
                            email_data = EmailService.get_upcoming_voting_with_registration_email_data(
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
                            email_data = EmailService.get_militante_registration_email_data(
                                to_email=item.recipient_email,
                                nombre=item.recipient_name,
                                registration_link=registration_link
                            )
                        elif item.email_type == 'VOTING_REMINDER':
                            email_data = EmailService.get_voting_reminder_email_data(
                                to_email=item.recipient_email,
                                user_name=item.recipient_name,
                                voting_title=item.voting.title,
                            )
                        batch_payload.append(email_data)
                        item_data_map[item.id] = email_data
                    except Exception as e:
                        item.status = 'FAILED'
                        item.error_message = str(e)
                        item.save()
                        upload_log.emails_failed += 1
                        errors = upload_log.details.get('email_errors', [])
                        if len(errors) < 50:
                            errors.append(f"{item.recipient_email}: {str(e)}")
                            upload_log.details['email_errors'] = errors
                        upload_log.save()

                if not batch_payload:
                    continue

                # === FASE 3: Enviar por Resend Batch API (con fallback SMTP) ===
                success = EmailService.send_resend_batch(batch_payload)

                if success:
                    # Marcar todo el lote como SENT de golpe
                    sent_ids = [item.id for item in batch_items if item.id in item_data_map]
                    EmailQueueItem.objects.filter(id__in=sent_ids).update(status='SENT')
                    upload_log.emails_sent += len(sent_ids)
                    upload_log.save()
                else:
                    # Fallback: enviar uno a uno por SMTP
                    for item in batch_items:
                        if item.id not in item_data_map:
                            continue
                        try:
                            if item.email_type == 'UPCOMING_VOTING':
                                voting = item.voting
                                start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                                finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
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
                                start_date = voting.start_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
                                finish_date = voting.finish_date.astimezone(santiago_tz).strftime('%d/%m/%Y %H:%M')
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
                            elif item.email_type == 'VOTING_REMINDER':
                                EmailService.send_voting_reminder_email(
                                    to_email=item.recipient_email,
                                    user_name=item.recipient_name,
                                    voting_title=item.voting.title,
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
                            if len(errors) < 50:
                                errors.append(f"{item.recipient_email}: {str(e)}")
                                upload_log.details['email_errors'] = errors
                            upload_log.save()

            # Finalizar log
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
        """
        Reanuda el procesamiento de colas con items PENDING.
        
        PROTECCIÓN: NO resetea items PROCESSING → PENDING.
        Si un item está en PROCESSING, es porque un hilo lo está manejando activamente.
        Resetearlo causaría envíos duplicados.
        """
        import threading
        from voting.models import DataUploadLog, EmailQueueItem
        from django.db import close_old_connections
        close_old_connections()
        try:
            logs_in_progress = DataUploadLog.objects.filter(details__in_progress=True)
            for log in logs_in_progress:
                # Solo reanudar si hay items genuinamente PENDING
                has_pending = EmailQueueItem.objects.filter(
                    upload_log=log, status='PENDING'
                ).exists()
                if has_pending:
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
