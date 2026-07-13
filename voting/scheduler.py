from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.core.management import call_command
import logging
import pytz

logger = logging.getLogger(__name__)

def run_send_start_reminders():
    try:
        call_command('send_start_reminders')
    except Exception as e:
        logger.error(f"Error executing send_start_reminders: {e}")

def start():
    # Inicializar con zona horaria de Chile
    scheduler = BackgroundScheduler(timezone=pytz.timezone('America/Santiago'))
    
    # Agregar tarea para ejecutarse cada 1 minuto
    scheduler.add_job(
        run_send_start_reminders,
        trigger=IntervalTrigger(minutes=1),
        id='send_start_reminders_job',
        max_instances=1,
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("APScheduler iniciado para send_start_reminders.")
