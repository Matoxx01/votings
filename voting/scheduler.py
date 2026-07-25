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

def run_verify_chains():
    try:
        from voting.models import Voting
        from voting.security import SecurityService
        from voting.time_utils import get_real_now
        
        # Obtener votaciones activas
        now = get_real_now()
        active_votings = Voting.objects.filter(
            start_date__lte=now,
            finish_date__gte=now
        )
        
        for voting in active_votings:
            SecurityService.verify_voting_chain(voting.id)
            
    except Exception as e:
        logger.error(f"Error executing run_verify_chains: {e}")

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
    
    # Agregar tarea para verificar la integridad de la cadena cada 10 minutos
    scheduler.add_job(
        run_verify_chains,
        trigger=IntervalTrigger(minutes=10),
        id='verify_voting_chains_job',
        max_instances=1,
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("APScheduler iniciado para send_start_reminders y verify_chains.")
