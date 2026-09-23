import uuid
from django.db import models


class ActionType(models.TextChoices):
    CREATE = 'CREATE', 'Création'
    UPDATE = 'UPDATE', 'Modification'
    DELETE = 'DELETE', 'Suppression'
    DEACTIVATE = 'DEACTIVATE', 'Désactivation'
    REACTIVATE = 'REACTIVATE', 'Réactivation'
    CANCEL = 'CANCEL', 'Annulation'
    LOGIN = 'LOGIN', 'Connexion'
    LOGOUT = 'LOGOUT', 'Déconnexion'


class Historique(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey('accounts.Utilisateur', on_delete=models.SET_NULL,
                                    null=True, related_name='historique')
    action = models.CharField('Action', max_length=20, choices=ActionType.choices)
    module = models.CharField('Module', max_length=50)
    objet_id = models.CharField('Objet ID', max_length=64, blank=True)
    description = models.TextField('Description', blank=True)
    adresse_ip = models.GenericIPAddressField('Adresse IP', null=True, blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historique'
        verbose_name_plural = 'Historiques'
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['-date_action']),
            models.Index(fields=['module']),
        ]

    def __str__(self):
        return f"[{self.date_action:%Y-%m-%d %H:%M}] {self.utilisateur} - {self.action} - {self.module}"