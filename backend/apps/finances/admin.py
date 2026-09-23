from django.contrib import admin
from .models import Paiement, ContributionAttendue


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'partenaire', 'montant', 'devise',
                    'date_paiement', 'mode_paiement', 'statut', 'enregistre_par')
    list_filter = ('statut', 'mode_paiement', 'devise')
    search_fields = ('reference', 'partenaire__code_partenaire', 'partenaire__nom')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    date_hierarchy = 'date_paiement'


@admin.register(ContributionAttendue)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('partenaire', 'periode_debut', 'periode_fin',
                    'montant_attendu', 'montant_paye', 'solde', 'statut')
    list_filter = ('statut',)
    search_fields = ('partenaire__code_partenaire', 'partenaire__nom')