from django.core.management.base import BaseCommand
from voting.services import EmailQueueService
from voting.models import DataUploadLog, EmailQueueItem


class Command(BaseCommand):
    help = 'Reanuda y procesa los correos pendientes en la cola de base de datos tras un reinicio o despliegue'

    def handle(self, *args, **options):
        self.stdout.write("Buscando cargas atascadas o correos pendientes en la base de datos...")
        
        logs_in_progress = DataUploadLog.objects.filter(details__in_progress=True)
        pending_items = EmailQueueItem.objects.filter(status__in=['PENDING', 'PROCESSING'])

        if not logs_in_progress.exists() and not pending_items.exists():
            self.stdout.write(self.style.SUCCESS("No se encontraron envíos pendientes ni cargas atascadas en progreso."))
            return

        self.stdout.write(f"Se encontraron {logs_in_progress.count()} cargas en progreso y {pending_items.count()} correos en cola.")
        self.stdout.write("Iniciando reanudación en segundo plano...")
        
        EmailQueueService.resume_all_pending_queues()
        
        self.stdout.write(self.style.SUCCESS("¡Reanudación iniciada con éxito!"))
