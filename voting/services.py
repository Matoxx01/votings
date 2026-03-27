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
    def send_upcoming_voting_email(to_email, nombre, voting_title, voting_description, start_date, finish_date):
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
    def send_bulk_upcoming_voting_emails(militantes, voting, delay=1):
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
        
        for i, militante in enumerate(militantes):
            try:
                EmailService.send_upcoming_voting_email(
                    to_email=militante.mail,
                    nombre=militante.nombre,
                    voting_title=voting.title,
                    voting_description=voting.description,
                    start_date=start_date,
                    finish_date=finish_date,
                )
                
                results['sent'] += 1
                
                if i < len(militantes) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{militante.mail}: {str(e)}")
        
        return results

    @staticmethod
    def send_bulk_registration_emails(users_data, base_url, delay=1):
        """
        Envía correos de registro masivamente con delay
        
        Args:
            users_data: Lista de diccionarios con {nombre, rut, mail, token}
            base_url: URL base del sitio
            delay: Segundos entre cada envío (default 1)
            
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
