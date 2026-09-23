import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.partenaires.models import Partenaire, Devise


class ModePaiement(models.TextChoices):
    ESPECES = 'ESPECES', 'Espèces'
    BANQUE = 'BANQUE', 'Banque'
    MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
    VIREMENT = 'VIREMENT', 'Virement'
    CHEQUE = 'CHEQUE', 'Chèque'
    AUTRE = 'AUTRE', 'Autre'


class StatutPaiement(models.TextChoices):
    ACTIF = 'ACTIF', 'Actif'
    ANNULE = 'ANNULE', 'Annulé'


class StatutContribution(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    PARTIEL = 'PARTIEL', 'Partiel'
    PAYE = 'PAYE', 'Payé'
    EN_RETARD = 'EN_RETARD', 'En retard'
    ANNULE = 'ANNULE', 'Annulé'


class Paiement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField('Référence', max_length=40, unique=True, blank=True)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.PROTECT,
                                    related_name='paiements', verbose_name='Partenaire')
    montant = models.DecimalField('Montant', max_digits=12, decimal_places=2)
    devise = models.CharField('Devise', max_length=5, choices=Devise.choices, default=Devise.USD)
    date_paiement = models.DateField('Date paiement', default=timezone.now)
    periode_debut = models.DateField('Début période')
    periode_fin = models.DateField('Fin période')
    mode_paiement = models.CharField('Mode', max_length=20, choices=ModePaiement.choices)
    reference_transaction = models.CharField('Réf. transaction', max_length=100, blank=True)
    commentaire = models.TextField('Commentaire', blank=True)
    enregistre_par = models.ForeignKey('accounts.Utilisateur', on_delete=models.PROTECT,
                                        related_name='paiements_enregistres', verbose_name='Enregistré par')
    statut = models.CharField('Statut', max_length=20, choices=StatutPaiement.choices,
                              default=StatutPaiement.ACTIF)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_paiement', '-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['date_paiement']),
            models.Index(fields=['partenaire', 'statut']),
        ]

    def __str__(self):
        return f"{self.reference} - {self.partenaire.nom_complet} ({self.montant} {self.devise})"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generer_reference()
        super().save(*args, **kwargs)

    def generer_reference(self):
        """PAY-YYYYMMDD-XXXX"""
        today = timezone.now().strftime('%Y%m%d')
        prefix = f"PAY-{today}-"
        dernier = Paiement.objects.filter(reference__startswith=prefix).order_by('-reference').first()
        if dernier:
            try:
                num = int(dernier.reference.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"


class ContributionAttendue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE,
                                    related_name='contributions_attendues')
    periode_debut = models.DateField('Début période')
    periode_fin = models.DateField('Fin période')
    date_echeance = models.DateField('Date échéance')
    montant_attendu = models.DecimalField('Montant attendu', max_digits=12, decimal_places=2)
    montant_paye = models.DecimalField('Montant payé', max_digits=12, decimal_places=2, default=0)
    solde = models.DecimalField('Solde', max_digits=12, decimal_places=2, default=0)
    statut = models.CharField('Statut', max_length=20, choices=StatutContribution.choices,
                              default=StatutContribution.EN_ATTENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contribution attendue'
        verbose_name_plural = 'Contributions attendues'
        ordering = ['-periode_debut']
        unique_together = ('partenaire', 'periode_debut', 'periode_fin')

    def __str__(self):
        return f"{self.partenaire.code_partenaire} {self.periode_debut} → {self.periode_fin}"

    def recalculer(self):
        """Recalcule montant_paye, solde et statut"""
        from django.db.models import Sum
        total = self.partenaire.paiements.filter(
            statut=StatutPaiement.ACTIF,
            periode_debut__gte=self.periode_debut,
            periode_fin__lte=self.periode_fin,
        ).aggregate(t=Sum('montant'))['t'] or Decimal('0')

        self.montant_paye = total
        self.solde = self.montant_attendu - total

        if self.solde <= 0:
            self.statut = StatutContribution.PAYE
        elif total > 0:
            self.statut = StatutContribution.PARTIEL
        elif self.date_echeance < timezone.now().date():
            self.statut = StatutContribution.EN_RETARD
        else:
            self.statut = StatutContribution.EN_ATTENTE

        self.save(update_fields=['montant_paye', 'solde', 'statut', 'updated_at'])