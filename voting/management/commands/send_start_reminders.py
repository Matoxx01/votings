from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from voting.models import Voting, Militante, UserData, DataUploadLog, APICounter
from voting.services import EmailQueueService
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Encola todas las votaciones activas y procesa solo un bulk/votación a la vez para no colapsar Resend, con bloqueo global de concurrencia'

    def handle(self, *args, **options):
        now = timezone.now()
        current_time = int(time.time())

        # 1. Verificamos el bloqueo global en APICounter para garantizar que solo un proceso en todo el sistema envíe bulks a la vez
        lock_obj, _ = APICounter.objects.get_or_create(name='START_REMINDER_LOCK', defaults={'contador': 0})

        # Si otro proceso actualizó el lock hace menos de 5 minutos (300 segundos), significa que hay un envío en curso
        if current_time - lock_obj.contador < 300:
            self.stdout.write("AVISO: Ya hay un proceso enviando bulks a Resend actualmente (lock activo). Se respetará la cola y se enviará solo un bulk a la vez para no colapsar Resend.")
            return

        # Adquirimos/renovamos el lock marcando el timestamp actual
        APICounter.objects.filter(name='START_REMINDER_LOCK').update(contador=current_time)

        try:
            # 2. Encolamos todas las votaciones activas que no hayan enviado el recordatorio
            votings = Voting.objects.filter(start_date__lte=now, finish_date__gte=now, start_reminder_sent=False).order_by('start_date')
            self.stdout.write(f"Votaciones activas pendientes de encolar: {votings.count()}")

            for voting in votings:
                with transaction.atomic():
                    locked_voting = Voting.objects.select_for_update().filter(pk=voting.pk, start_reminder_sent=False).first()
                    if not locked_voting:
                        continue

                    log_exists = DataUploadLog.objects.filter(upload_type='START_REMINDER', voting=locked_voting).exists()
                    if not log_exists:
                        ruts = UserData.objects.filter(id_voting=locked_voting).values_list('rut', flat=True)
                        militantes = Militante.objects.filter(rut__in=ruts, is_active=True)

                        upload_log = DataUploadLog.objects.create(
                            upload_type='START_REMINDER',
                            voting=locked_voting,
                            file_name=f"Recordatorio Votacion {locked_voting.id} - {locked_voting.title[:100]}",
                            total_rows=militantes.count(),
                            details={'in_progress': False}
                        )

                        EmailQueueService.queue_voting_reminder_emails(militantes, locked_voting, settings.SITE_URL, upload_log)
                        self.stdout.write(self.style.SUCCESS(f"Votación '{locked_voting.title}': {militantes.count()} correos puestos en cola."))
                    else:
                        self.stdout.write(f"Votación '{locked_voting.title}': ya tenía correos en cola.")

                    locked_voting.start_reminder_sent = True
                    locked_voting.save(update_fields=['start_reminder_sent'])

            # 3. Procesar las colas: SOLO UN BULK A LA VEZ (tomamos solo el primer log pendiente)
            pending_logs = DataUploadLog.objects.filter(
                upload_type='START_REMINDER',
                queue_items__status='PENDING'
            ).distinct().order_by('created_at')

            total_pending = pending_logs.count()
            self.stdout.write(f"Logs de votaciones en cola total: {total_pending}")

            if total_pending == 0:
                self.stdout.write("No hay correos pendientes de envío.")
                return

            # Tomamos exclusivamente el primer log para procesar un solo bulk a la vez
            log = pending_logs.first()
            self.stdout.write(f"Procesando UN SOLO BULK a la vez: votación '{log.voting.title if log.voting else log.file_name}' (Log ID: {log.id})...")
            
            EmailQueueService.process_queue_for_log(log.id)
            
            log.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(
                f"Votación '{log.voting.title if log.voting else log.file_name}': correos enviados={log.emails_sent}, fallidos={log.emails_failed}"
            ))
            
            if total_pending > 1:
                self.stdout.write(self.style.NOTICE(f"Quedan {total_pending - 1} votaciones en cola que serán procesadas en la siguiente ejecución para no colapsar Resend."))

        finally:
            # Liberamos el bloqueo global al finalizar
            APICounter.objects.filter(name='START_REMINDER_LOCK').update(contador=0)
