import uuid
from django.db import models


class TypeNotification(models.TextChoices):
    INFO = 'INFO', 'Information'
    WARNING = 'WARNING', 'Avertissement'
    SUCCESS = 'SUCCESS', 'Succès'
    DANGER = 'DANGER', 'Alerte'


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey('accounts.Utilisateur', on_delete=models.CASCADE,
                                      related_name='notifications')
    titre = models.CharField('Titre', max_length=200)
    message = models.TextField('Message')
    type = models.CharField('Type', max_length=20, choices=TypeNotification.choices,
                            default=TypeNotification.INFO)
    lu = models.BooleanField('Lu', default=False)
    lien = models.CharField('Lien', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.titre} → {self.destinataire}"