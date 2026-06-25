from django.apps import AppConfig
import threading
import time


class VotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voting"

    def ready(self):
        # Iniciar reanudación automática en segundo plano tras 5 segundos
        def auto_resume():
            time.sleep(5)
            try:
                from voting.services import EmailQueueService
                EmailQueueService.resume_all_pending_queues()
            except Exception:
                pass

        thread = threading.Thread(target=auto_resume)
        thread.daemon = True
        thread.start()
