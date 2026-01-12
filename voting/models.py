from django.db import models
from django.utils import timezone


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
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Voting"
        verbose_name_plural = "Votings"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_open(self):
        """Verifica si la votación está activa"""
        now = timezone.now()
        return self.start_date <= now <= self.finish_date and self.is_active


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
        """Obtiene el total de votos para este subject"""
        count = Count.objects.filter(id_subject=self).first()
        return count.number if count else 0


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


class UserData(models.Model):
    """Modelo para datos de usuarios autorizados a votar"""
    id_voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='user_data')
    rut = models.CharField(max_length=20)
    has_voted = models.BooleanField(default=False)
    voted_at = models.DateTimeField(null=True, blank=True)
    register = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Data"
        verbose_name_plural = "Users Data"
        unique_together = ['id_voting', 'rut']

    def __str__(self):
        return f"{self.rut} - {self.id_voting.title}"


class VotingRecord(models.Model):
    """Modelo para registrar los votos realizados"""
    id_voting = models.ForeignKey(Voting, on_delete=models.CASCADE)
    id_subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    user_data = models.ForeignKey(UserData, on_delete=models.CASCADE)
    rut = models.CharField(max_length=20)
    mail = models.EmailField()
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Voting Record"
        verbose_name_plural = "Voting Records"

    def __str__(self):
        return f"{self.rut} votó por {self.id_subject.name}"
