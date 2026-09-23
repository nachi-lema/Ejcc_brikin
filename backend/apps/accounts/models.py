import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrateur'
    TRESORIER = 'TRESORIER', 'Trésorier'
    AGENT = 'AGENT', 'Agent'
    CONSULTATION = 'CONSULTATION', 'Consultation'


class Utilisateur(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField('Téléphone', max_length=30, blank=True)
    role = models.CharField('Rôle', max_length=20, choices=Role.choices, default=Role.AGENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_tresorier(self):
        return self.role == Role.TRESORIER

    @property
    def is_agent(self):
        return self.role == Role.AGENT

    @property
    def is_consultation(self):
        return self.role == Role.CONSULTATION

    # Permissions métier
    @property
    def peut_gerer_partenaires(self):
        return self.role in (Role.ADMIN, Role.TRESORIER, Role.AGENT)

    @property
    def peut_gerer_finances(self):
        return self.role in (Role.ADMIN, Role.TRESORIER)

    @property
    def peut_voir_rapports(self):
        return self.role in (Role.ADMIN, Role.TRESORIER, Role.CONSULTATION)