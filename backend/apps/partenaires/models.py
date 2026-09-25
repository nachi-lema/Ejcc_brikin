import uuid
from django.db import models
from django.utils import timezone


class TypePartenaire(models.TextChoices):
    PARTICULIER = 'PARTICULIER', 'Particulier'
    ORGANISATION = 'ORGANISATION', 'Organisation'
    MEMBRE = 'MEMBRE', 'Membre'


class Frequence(models.TextChoices):
    MENSUELLE = 'MENSUELLE', 'Mensuelle'
    TRIMESTRIELLE = 'TRIMESTRIELLE', 'Trimestrielle'
    SEMESTRIELLE = 'SEMESTRIELLE', 'Semestrielle'
    ANNUELLE = 'ANNUELLE', 'Annuelle'
    PONCTUELLE = 'PONCTUELLE', 'Ponctuelle'


class Devise(models.TextChoices):
    USD = 'USD', 'USD ($)'
    CDF = 'CDF', 'CDF (FC)'


class StatutPartenaire(models.TextChoices):
    ACTIF = 'ACTIF', 'Actif'
    DESACTIVE = 'DESACTIVE', 'Désactivé'


class Partenaire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_partenaire = models.CharField('Code', max_length=30, unique=True, blank=True)
    nom = models.CharField('Nom', max_length=100)
    postnom = models.CharField('Postnom', max_length=100, blank=True)
    prenom = models.CharField('Prénom', max_length=100, blank=True)
    telephone = models.CharField('Téléphone', max_length=30)
    email = models.EmailField('Email', blank=True)
    adresse = models.CharField('Adresse', max_length=255, blank=True)
    type_partenaire = models.CharField('Type', max_length=20, choices=TypePartenaire.choices, default=TypePartenaire.PARTICULIER)
    date_adhesion = models.DateField('Date d\'adhésion', default=timezone.now)
    montant_contribution = models.DecimalField('Montant contribution', max_digits=12, decimal_places=2, default=0)
    frequence = models.CharField('Fréquence', max_length=20, choices=Frequence.choices, default=Frequence.MENSUELLE)
    devise = models.CharField('Devise', max_length=5, choices=Devise.choices, default=Devise.USD)
    statut = models.CharField('Statut', max_length=20, choices=StatutPartenaire.choices, default=StatutPartenaire.ACTIF)
    observation = models.TextField('Observation', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    desactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Partenaire'
        verbose_name_plural = 'Partenaires'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code_partenaire']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"{self.code_partenaire} - {self.nom_complet}"

    @property
    def nom_complet(self):
        parts = [self.nom, self.postnom, self.prenom]
        return ' '.join(p for p in parts if p).strip()

    def save(self, *args, **kwargs):
        if not self.code_partenaire:
            self.code_partenaire = self.generer_code()
        super().save(*args, **kwargs)

    def generer_code(self):
        """Génère un code unique PART-YYYY-XXXX"""
        annee = timezone.now().year
        prefix = f"PART-{annee}-"
        dernier = Partenaire.objects.filter(code_partenaire__startswith=prefix).order_by('-code_partenaire').first()
        if dernier:
            try:
                num = int(dernier.code_partenaire.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"

    def desactiver(self):
        self.statut = StatutPartenaire.DESACTIVE
        self.desactivated_at = timezone.now()
        self.save(update_fields=['statut', 'desactivated_at', 'updated_at'])

    def reactiver(self):
        self.statut = StatutPartenaire.ACTIF
        self.desactivated_at = None
        self.save(update_fields=['statut', 'desactivated_at', 'updated_at'])

    # Agrégats financiers
    @property
    def total_paye(self):
        from apps.finances.models import Paiement, StatutPaiement
        return self.paiements.filter(statut=StatutPaiement.ACTIF).aggregate(
            total=models.Sum('montant'))['total'] or 0

    @property
    def solde(self):
        from apps.finances.models import ContributionAttendue, StatutContribution
        total_attendu = self.contributions_attendues.exclude(
            statut=StatutContribution.ANNULE).aggregate(
            total=models.Sum('montant_attendu'))['total'] or 0
        return total_attendu - self.total_paye