"""
Servicio centralizado de seguridad y auditoría.

Registra eventos de seguridad en base de datos y provee
utilidades de bloqueo de IP y verificación de integridad.
"""
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Obtiene la IP real del cliente (compatible con el rate_limit.py corregido)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        ips = [ip.strip() for ip in xff.split(',')]
        return ips[-2] if len(ips) >= 2 else ips[0]
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


class SecurityService:
    """Servicio centralizado de seguridad y auditoría"""

    @staticmethod
    def log_event(event_type, severity, description, request=None, voting=None,
                  militante_rut='', maintainer=None, details=None):
        """
        Registra un evento de seguridad en la base de datos.
        
        Args:
            event_type: Tipo de evento (LOGIN_FAILED, CHAIN_INTEGRITY_FAIL, etc.)
            severity: INFO, MEDIUM, HIGH, CRITICAL
            description: Descripción legible del evento
            request: HttpRequest (opcional, para extraer IP y User-Agent)
            voting: Instancia de Voting (opcional)
            militante_rut: RUT del militante involucrado (opcional)
            maintainer: Instancia de Maintainer (opcional)
            details: dict con datos extra (opcional)
        """
        from voting.models import SecurityEvent
        
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = _get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            SecurityEvent.objects.create(
                event_type=event_type,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                voting=voting,
                militante_rut=militante_rut,
                maintainer=maintainer,
                details=details or {},
            )
        except Exception as e:
            # Nunca dejar que un fallo de logging rompa la funcionalidad principal
            logger.error(f"Error registrando evento de seguridad: {e}")

    @staticmethod
    def verify_voting_chain(voting_id):
        """
        Verifica la cadena de integridad de una votación y registra el resultado.
        
        Returns:
            tuple: (ok: bool, broken_at: int|None, total_votes: int)
        """
        from voting.models import VotingRecord, Voting
        
        try:
            voting = Voting.objects.get(id=voting_id)
        except Voting.DoesNotExist:
            return False, None, 0
        
        total_votes = VotingRecord.objects.filter(id_voting_id=voting_id).count()
        ok, broken_at = VotingRecord.verify_chain(voting_id)
        
        if ok:
            SecurityService.log_event(
                event_type='CHAIN_INTEGRITY_OK',
                severity='INFO',
                description=f'Verificación de cadena exitosa para "{voting.title}" ({total_votes} votos verificados)',
                voting=voting,
                details={'total_votes': total_votes},
            )
        else:
            SecurityService.log_event(
                event_type='CHAIN_INTEGRITY_FAIL',
                severity='CRITICAL',
                description=f'¡ALERTA! Cadena de integridad ROTA en "{voting.title}" en el registro PK={broken_at}',
                voting=voting,
                details={'broken_at_pk': broken_at, 'total_votes': total_votes},
            )
        
        return ok, broken_at, total_votes

    @staticmethod
    def get_events_summary(hours=24):
        """
        Obtiene un resumen de eventos de seguridad de las últimas N horas.
        
        Returns:
            dict con contadores por severidad y totales
        """
        from voting.models import SecurityEvent
        
        since = timezone.now() - timedelta(hours=hours)
        events = SecurityEvent.objects.filter(created_at__gte=since)
        
        return {
            'total': events.count(),
            'critical': events.filter(severity='CRITICAL').count(),
            'high': events.filter(severity='HIGH').count(),
            'medium': events.filter(severity='MEDIUM').count(),
            'info': events.filter(severity='INFO').count(),
            'login_failed': events.filter(event_type='LOGIN_FAILED').count(),
            'rate_limited': events.filter(event_type='RATE_LIMITED').count(),
        }

    @staticmethod
    def block_ip(ip_address, reason, blocked_by_maintainer):
        """Bloquea una IP permanentemente."""
        from voting.models import SecurityBlockedIP
        
        obj, created = SecurityBlockedIP.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'reason': reason,
                'blocked_by': blocked_by_maintainer,
                'is_active': True,
            }
        )
        
        SecurityService.log_event(
            event_type='IP_BLOCKED',
            severity='HIGH',
            description=f'IP {ip_address} bloqueada por {blocked_by_maintainer}: {reason}',
            maintainer=blocked_by_maintainer,
            details={'ip': ip_address, 'reason': reason},
        )
        
        return obj, created

    @staticmethod
    def unblock_ip(block_id, unblocked_by_maintainer):
        """Desbloquea una IP."""
        from voting.models import SecurityBlockedIP
        
        try:
            block = SecurityBlockedIP.objects.get(id=block_id)
            ip = block.ip_address
            block.is_active = False
            block.save()
            
            SecurityService.log_event(
                event_type='IP_UNBLOCKED',
                severity='INFO',
                description=f'IP {ip} desbloqueada por {unblocked_by_maintainer}',
                maintainer=unblocked_by_maintainer,
                details={'ip': ip},
            )
            return True
        except SecurityBlockedIP.DoesNotExist:
            return False

    @staticmethod
    def is_ip_blocked(ip_address):
        """Verifica si una IP está bloqueada."""
        from voting.models import SecurityBlockedIP
        return SecurityBlockedIP.objects.filter(
            ip_address=ip_address, is_active=True
        ).exists()

    @staticmethod
    def cleanup_old_events(days=90):
        """Elimina eventos de seguridad con más de N días de antigüedad."""
        from voting.models import SecurityEvent
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count, _ = SecurityEvent.objects.filter(created_at__lt=cutoff).delete()
        logger.info(f"Limpieza de seguridad: {deleted_count} eventos eliminados (>{days} días)")
        return deleted_count
