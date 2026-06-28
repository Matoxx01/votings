from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from voting.models import Voting, Militante, UserData, DataUploadLog
from voting.services import EmailQueueService
import time


class Command(BaseCommand):
    help = 'Encola y envía correos recordatorios cuando una votación empieza usando Resend Bulk API de forma secuencial y segura'

    def handle(self, *args, **options):
        now = timezone.now()
        # Buscamos votaciones activas (start_date <= now <= finish_date) que no hayan enviado el recordatorio
        votings = Voting.objects.filter(start_date__lte=now, finish_date__gte=now, start_reminder_sent=False).order_by('start_date')

        self.stdout.write(f"Votaciones activas pendientes de encolar: {votings.count()}")

        for voting in votings:
            # Proteccion extrema contra concurrencia: usamos transacción atómica y bloqueo de fila
            with transaction.atomic():
                # Bloqueamos el registro de la votación para asegurarnos de que ningún otro proceso la modifique al mismo tiempo
                locked_voting = Voting.objects.select_for_update().filter(pk=voting.pk, start_reminder_sent=False).first()
                if not locked_voting:
                    # Otro proceso ya la procesó
                    continue

                # Verificamos si ya existe un DataUploadLog para esta votación para evitar encolar duplicados
                log_exists = DataUploadLog.objects.filter(upload_type='START_REMINDER', voting=locked_voting).exists()
                if not log_exists:
                    # Obtener ruts autorizados para la votación
                    ruts = UserData.objects.filter(id_voting=locked_voting).values_list('rut', flat=True)
                    militantes = Militante.objects.filter(rut__in=ruts, is_active=True)

                    # Crear log de envío
                    upload_log = DataUploadLog.objects.create(
                        upload_type='START_REMINDER',
                        voting=locked_voting,
                        file_name=f"Recordatorio Votacion {locked_voting.id} - {locked_voting.title[:100]}",
                        total_rows=militantes.count(),
                        details={'in_progress': False}
                    )

                    # Encolar los correos
                    EmailQueueService.queue_voting_reminder_emails(militantes, locked_voting, upload_log)
                    self.stdout.write(self.style.SUCCESS(f"Votación '{locked_voting.title}': {militantes.count()} correos puestos en cola."))
                else:
                    self.stdout.write(f"Votación '{locked_voting.title}': ya tenía correos en cola.")

                # Marcamos inmediatamente como enviado para que no se vuelva a encolar en futuras ejecuciones
                locked_voting.start_reminder_sent = True
                locked_voting.save(update_fields=['start_reminder_sent'])

        # Procesar las colas secuencialmente: primero los de una votación y después las otras
        # Buscamos todos los logs de START_REMINDER que tengan items pendientes
        pending_logs = DataUploadLog.objects.filter(
            upload_type='START_REMINDER',
            queue_items__status='PENDING'
        ).distinct().order_by('created_at')

        self.stdout.write(f"Logs de votaciones en cola para enviar: {pending_logs.count()}")

        total_sent = 0
        total_failed = 0

        for log in pending_logs:
            self.stdout.write(f"Procesando cola para votación '{log.voting.title if log.voting else log.file_name}' (Log ID: {log.id})...")
            # process_queue_for_log procesa lotes de 100 usando resend batch, de forma síncrona en este bucle
            EmailQueueService.process_queue_for_log(log.id)
            
            # Refrescar log para ver resultados
            log.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(
                f"Votación '{log.voting.title if log.voting else log.file_name}': correos enviados={log.emails_sent}, fallidos={log.emails_failed}"
            ))
            total_sent += log.emails_sent
            total_failed += log.emails_failed

        self.stdout.write(self.style.SUCCESS(
            f"Resumen total de envíos en esta ejecución: enviados={total_sent}, fallidos={total_failed}"
        ))
