from django.db import models, connection
from django.utils import timezone
from django.conf import settings
import secrets
import datetime
import hmac
import hashlib
from .time_utils import get_real_now


class Region(models.Model):
    """Modelo para las regiones de Chile"""
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Region"
        verbose_name_plural = "Regiones"
        ordering = ['id']

    def __str__(self):
        return self.name


class Role(models.Model):
    """Modelo para los roles de los maintainers"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name


class User(models.Model):
    """Modelo para usuarios que votan"""
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    mail = models.EmailField(unique=True)
    rut = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.name} {self.lastname} ({self.rut})"


class Maintainer(models.Model):
    """Modelo para administradores del sistema"""
    id_role = models.ForeignKey(Role, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    mail = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Maintainer"
        verbose_name_plural = "Maintainers"

    def __str__(self):
        return f"{self.name} {self.lastname} ({self.mail})"


class Voting(models.Model):
    """Modelo para las votaciones"""
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='votings/', null=True, blank=True)
    id_region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='votings')
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Voting"
        verbose_name_plural = "Votings"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_open(self):
        """Verifica si la votación está activa según fechas (usando hora real de internet)"""
        now = get_real_now()
        return self.start_date <= now <= self.finish_date


class Subject(models.Model):
    """Modelo para los temas/opciones de votación"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    id_voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='subjects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

    def __str__(self):
        return f"{self.name} - {self.id_voting.title}"

    def get_vote_count(self):
        """Obtiene el total de votos para este subject (fuente de verdad: VotingRecords)"""
        return VotingRecord.objects.filter(id_subject=self).count()


class Count(models.Model):
    """Modelo para contar los votos por subject"""
    id_subject = models.OneToOneField(Subject, on_delete=models.CASCADE, related_name='vote_count')
    number = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Count"
        verbose_name_plural = "Counts"

    def __str__(self):
        return f"{self.id_subject.name}: {self.number} votos"

    def get_verified_count(self):
        """Obtiene el conteo real basado en VotingRecords (fuente de verdad)"""
        return VotingRecord.objects.filter(id_subject=self.id_subject).count()

    def is_consistent(self):
        """Verifica que el contador coincide con los registros reales"""
        return self.number == self.get_verified_count()


class UserData(models.Model):
    """Modelo para datos de usuarios autorizados a votar"""
    id_voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='user_data')
    rut = models.CharField(max_length=20)
    has_voted = models.BooleanField(default=False)
    register = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Data"
        verbose_name_plural = "Users Data"
        unique_together = ['id_voting', 'rut']

    def __str__(self):
        return f"{self.rut} - {self.id_voting.title}"


class VotingRecord(models.Model):
    """
    Registro inmutable de un voto (ANÓNIMO).
    
    Protecciones:
    - integrity_hash: HMAC del contenido del registro, impide modificar campos
    - chain_hash: incluye el hash del registro anterior de la misma votación (cadena)
      → cualquier INSERT/DELETE en medio de la cadena la rompe y es detectable
    - save() rechaza actualizaciones posteriores a la creación
    """
    id_voting = models.ForeignKey(Voting, on_delete=models.CASCADE)
    id_subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    integrity_hash = models.CharField(max_length=64, blank=True)
    chain_hash = models.CharField(max_length=64, blank=True,
                                   help_text='Hash encadenado con el voto anterior de esta votación')

    class Meta:
        verbose_name = "Voting Record"
        verbose_name_plural = "Voting Records"

    def __str__(self):
        return f"Voto por {self.id_subject.name} en {self.id_voting.title}"

    @staticmethod
    def _get_prev_chain_hash(voting_id, exclude_pk=None):
        """Obtiene el chain_hash del último registro de la votación (eslabón anterior)."""
        qs = VotingRecord.objects.filter(id_voting_id=voting_id)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        prev = qs.order_by('pk').last()
        return prev.chain_hash if prev else '0' * 64

    def generate_hash(self, prev_chain_hash=None):
        """
        Genera el HMAC del registro.
        Incluye el hash encadenado del registro anterior, de modo que:
        - Modificar cualquier campo invalida este hash
        - Insertar/borrar un registro en la cadena invalida todos los hashes posteriores
        """
        if prev_chain_hash is None:
            prev_chain_hash = VotingRecord._get_prev_chain_hash(self.id_voting_id, exclude_pk=self.pk)
        message = f"{self.id_voting_id}:{self.id_subject_id}:{self.pk}:{prev_chain_hash}"
        return hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_integrity(self):
        """Verifica que el registro no ha sido alterado."""
        return hmac.compare_digest(self.integrity_hash, self.generate_hash())

    @staticmethod
    def verify_chain(voting_id):
        """
        Verifica la integridad de toda la cadena de votos de una votación.
        Retorna (ok: bool, broken_at: int|None) donde broken_at es el pk del primer fallo.
        """
        records = list(VotingRecord.objects.filter(id_voting_id=voting_id).order_by('pk'))
        prev_hash = '0' * 64
        for record in records:
            expected = hmac.new(
                settings.SECRET_KEY.encode(),
                f"{record.id_voting_id}:{record.id_subject_id}:{record.pk}:{prev_hash}".encode(),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(record.integrity_hash, expected):
                return False, record.pk
            prev_hash = record.integrity_hash
        return True, None

    def save(self, *args, **kwargs):
        # Bloquear cualquier actualización posterior a la creación inicial
        if self.pk and not kwargs.get('update_fields') == ['integrity_hash']:
            existing = VotingRecord.objects.filter(pk=self.pk).exists()
            if existing:
                raise PermissionError(
                    "Los registros de votos son inmutables y no pueden ser modificados."
                )
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new and not self.integrity_hash:
            prev_chain_hash = VotingRecord._get_prev_chain_hash(self.id_voting_id, exclude_pk=self.pk)
            self.integrity_hash = self.generate_hash(prev_chain_hash=prev_chain_hash)
            self.chain_hash = self.integrity_hash
            # Usamos update() para no disparar el save() recursivo con restricción.
            # En MySQL/MariaDB habilitamos una bandera SQL de autorización temporal.
            if connection.vendor == 'mysql':
                with connection.cursor() as cursor:
                    cursor.execute("SET @allow_votingrecord_update = 1")
                try:
                    VotingRecord.objects.filter(pk=self.pk).update(
                        integrity_hash=self.integrity_hash,
                        chain_hash=self.chain_hash,
                    )
                finally:
                    with connection.cursor() as cursor:
                        cursor.execute("SET @allow_votingrecord_update = 0")
            else:
                VotingRecord.objects.filter(pk=self.pk).update(
                    integrity_hash=self.integrity_hash,
                    chain_hash=self.chain_hash,
                )

    def delete(self, *args, **kwargs):
        raise PermissionError(
            "Los registros de votos son inmutables y no pueden ser eliminados."
        )

class PasswordResetToken(models.Model):
    """Modelo para tokens de recuperación de contraseña de maintainers"""
    maintainer = models.ForeignKey('Maintainer', on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
    
    def __str__(self):
        return f"Token para {self.maintainer.mail}"
    
    def is_valid(self):
        """Verifica si el token es válido (no expirado y no usado)"""
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def create_token(maintainer):
        """Crea un nuevo token de recuperación"""
        # Generar token único
        token = secrets.token_urlsafe(32)
        # Expiración en 24 horas
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        return PasswordResetToken.objects.create(
            maintainer=maintainer,
            token=token,
            expires_at=expires_at
        )


class Militante(models.Model):
    """Modelo para militantes registrados que pueden votar"""
    nombre = models.CharField(max_length=200)
    rut = models.CharField(max_length=20, unique=True)
    mail = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Militante"
        verbose_name_plural = "Militantes"
    
    def __str__(self):
        return f"{self.nombre} ({self.rut})"


class MilitanteRegistrationToken(models.Model):
    """Modelo para tokens de registro de militantes"""
    nombre = models.CharField(max_length=200)
    rut = models.CharField(max_length=20)
    mail = models.EmailField()
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Militante Registration Token"
        verbose_name_plural = "Militante Registration Tokens"
    
    def __str__(self):
        return f"Token de registro para {self.mail}"
    
    def is_valid(self):
        """Verifica si el token es válido (no expirado y no usado)"""
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def create_token(nombre, rut, mail):
        """Crea un nuevo token de registro"""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + datetime.timedelta(hours=72)  # 72 horas para registrarse
        
        return MilitanteRegistrationToken.objects.create(
            nombre=nombre,
            rut=rut,
            mail=mail,
            token=token,
            expires_at=expires_at
        )


class MilitantePasswordResetToken(models.Model):
    """Modelo para tokens de recuperación de contraseña de militantes"""
    militante = models.ForeignKey('Militante', on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Militante Password Reset Token"
        verbose_name_plural = "Militante Password Reset Tokens"
    
    def __str__(self):
        return f"Token para {self.militante.mail}"
    
    def is_valid(self):
        """Verifica si el token es válido (no expirado y no usado)"""
        return not self.used and timezone.now() <= self.expires_at
    
    @staticmethod
    def create_token(militante):
        """Crea un nuevo token de recuperación"""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        return MilitantePasswordResetToken.objects.create(
            militante=militante,
            token=token,
            expires_at=expires_at
        )
