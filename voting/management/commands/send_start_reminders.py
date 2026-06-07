from django.core.management.base import BaseCommand
from django.utils import timezone
from voting.models import Voting, Militante, UserData
from voting.services import EmailService


class Command(BaseCommand):
    help = 'Envía correos recordatorios cuando una votación empieza (una sola vez)'

    def handle(self, *args, **options):
        now = timezone.now()
        votings = Voting.objects.filter(start_date__lte=now, start_reminder_sent=False)

        total_sent = 0
        total_failed = 0

        for voting in votings:
            # Obtener ruts autorizados para la votación
            ruts = UserData.objects.filter(id_voting=voting).values_list('rut', flat=True)
            militantes = Militante.objects.filter(rut__in=ruts, is_active=True)

            sent = 0
            failed = 0

            for militante in militantes:
                try:
                    EmailService.send_voting_reminder_email(
                        to_email=militante.mail,
                        user_name=militante.nombre,
                        voting_title=voting.title,
                    )
                    sent += 1
                except Exception as e:
                    failed += 1
                    self.stderr.write(f"Error al enviar a {militante.mail}: {e}")

            # Marcar que ya se enviaron los recordatorios de inicio para esta votación
            voting.start_reminder_sent = True
            voting.save(update_fields=['start_reminder_sent'])

            total_sent += sent
            total_failed += failed

            self.stdout.write(self.style.SUCCESS(
                f"Votación '{voting.title}': correos enviados={sent}, fallidos={failed}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Resumen total: enviados={total_sent}, fallidos={total_failed}"
        ))
