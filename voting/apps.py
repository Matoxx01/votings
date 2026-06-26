from django.apps import AppConfig
import threading
import time


class VotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voting"

    def ready(self):
        # PARADA DE EMERGENCIA Y LIMPIEZA TOTAL (100% ROBUSTA - EVITA MYSQL ERROR 1038)
        def emergency_stop():
            time.sleep(2)
            try:
                from voting.models import DataUploadLog, EmailQueueItem
                from django.db import close_old_connections
                close_old_connections()
                
                # 1. Cancelar correos primero (con su propio try/except)
                try:
                    EmailQueueItem.objects.filter(status__in=['PENDING', 'PROCESSING']).update(status='FAILED', error_message='Cancelado por parada de emergencia.')
                except Exception as e:
                    print("Error cancelando cola:", e)

                # 2. Limpiar logs atascados sorteando solo por ID (evita el error 1038 Out of sort memory de MySQL)
                try:
                    log_ids = list(DataUploadLog.objects.values_list('id', flat=True).order_by('-id')[:100])
                    for log_id in log_ids:
                        try:
                            log = DataUploadLog.objects.get(id=log_id)
                            if isinstance(log.details, dict):
                                modified = False
                                if log.details.get('in_progress'):
                                    log.details['in_progress'] = False
                                    log.details['process_error'] = 'Detenido por emergencia.'
                                    modified = True
                                if len(log.details.get('email_errors', [])) > 20:
                                    log.details['email_errors'] = log.details['email_errors'][:20]
                                    modified = True
                                if modified:
                                    log.save()
                        except Exception as ex:
                            print(f"Error limpiando log {log_id}:", ex)
                except Exception as e:
                    print("Error obteniendo IDs de DataUploadLog:", e)

            except Exception:
                pass
            finally:
                close_old_connections()

        thread = threading.Thread(target=emergency_stop)
        thread.daemon = True
        thread.start()
