from django.contrib import admin
from .models import Partenaire


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ('code_partenaire', 'nom_complet', 'telephone', 'type_partenaire',
                    'montant_contribution', 'devise', 'frequence', 'statut')
    list_filter = ('statut', 'type_partenaire', 'frequence', 'devise')
    search_fields = ('code_partenaire', 'nom', 'postnom', 'prenom', 'telephone')
    readonly_fields = ('code_partenaire', 'created_at', 'updated_at')