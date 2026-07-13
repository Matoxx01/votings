from django.apps import AppConfig
import os
import sys

class VotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voting"

    def ready(self):
        # Evitar correr en comandos como makemigrations, migrate, etc.
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0] or 'uvicorn' in sys.argv[0]:
            # Evitar correr 2 veces por el autoreloader en runserver
            if os.environ.get('RUN_MAIN', None) != 'true' and 'runserver' in sys.argv:
                pass
            else:
                try:
                    from voting import scheduler
                    scheduler.start()
                except Exception:
                    pass
