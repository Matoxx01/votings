from django.apps import AppConfig
import threading
import time


class VotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voting"

    def ready(self):
        # PARADA DE EMERGENCIA: DETENER ENVÍOS MASIVOS Y LIMPIAR LOGS ATASCADOS (Evitar Error 500)
        def emergency_stop():
            time.sleep(3)
            try:
                from voting.models import DataUploadLog, EmailQueueItem
                from django.db import close_old_connections
                close_old_connections()
                
                # 1. Marcar todos los logs en proceso como terminados y limpiar la lista gigante de errores para evitar el Error 500
                stuck_logs = DataUploadLog.objects.filter(details__in_progress=True)
                for log in stuck_logs:
                    log.details = {'in_progress': False, 'process_error': 'Detenido por emergencia para evitar envíos duplicados.'}
                    log.save()
                
                # 2. También limpiar cualquier log que tenga una lista de email_errors gigante que esté causando el Error 500
                problematic_logs = DataUploadLog.objects.filter(details__email_errors__isnull=False)
                for log in problematic_logs:
                    if len(log.details.get('email_errors', [])) > 50:
                        log.details['email_errors'] = log.details['email_errors'][:20]  # Dejar solo los primeros 20
                        log.save()

                # 3. Cancelar todos los correos pendientes o en proceso en la base de datos
                EmailQueueItem.objects.filter(status__in=['PENDING', 'PROCESSING']).update(status='FAILED', error_message='Cancelado por parada de emergencia.')
            except Exception:
                pass
            finally:
                close_old_connections()

        thread = threading.Thread(target=emergency_stop)
        thread.daemon = True
        thread.start()
