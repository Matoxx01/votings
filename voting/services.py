from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


class EmailService:
    """Servicio para enviar correos electrónicos"""

    @staticmethod
    def send_confirmation_email(to_email, user_name, voting_title, subject_name):
        """
        Envía un correo de confirmación de voto
        
        Args:
            to_email: Correo del votante
            user_name: Nombre del votante
            voting_title: Título de la votación
            subject_name: Nombre del subject votado
        """
        subject = f"Confirmación de Voto - {voting_title}"
        
        context = {
            'user_name': user_name,
            'voting_title': voting_title,
            'subject_name': subject_name,
        }
        
        html_message = render_to_string('voting/emails/confirmation_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
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
            settings.EMAIL_HOST_USER,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
