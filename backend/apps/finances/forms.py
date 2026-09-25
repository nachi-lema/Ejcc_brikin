from django import forms
from .models import Paiement, ContributionAttendue
from apps.partenaires.models import Partenaire


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['partenaire', 'montant', 'devise', 'date_paiement',
                  'periode_debut', 'periode_fin', 'mode_paiement',
                  'reference_transaction', 'commentaire']
        widgets = {
            'partenaire': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'devise': forms.Select(attrs={'class': 'form-select'}),
            'date_paiement': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periode_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periode_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'reference_transaction': forms.TextInput(attrs={'class': 'form-control'}),
            'commentaire': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inclure TOUS les partenaires (actifs en premier, désactivés en bas)
        qs = Partenaire.objects.all().order_by('statut', 'nom')
        self.fields['partenaire'].queryset = qs

    def clean(self):
        cleaned = super().clean()
        montant = cleaned.get('montant')
        debut = cleaned.get('periode_debut')
        fin = cleaned.get('periode_fin')
        if montant is not None and montant <= 0:
            raise forms.ValidationError("Le montant doit être strictement supérieur à 0.")
        if debut and fin and fin < debut:
            raise forms.ValidationError("La fin de période doit être postérieure au début.")
        return cleaned


class ContributionForm(forms.ModelForm):
    class Meta:
        model = ContributionAttendue
        fields = ['partenaire', 'periode_debut', 'periode_fin', 'date_echeance', 'montant_attendu']
        widgets = {
            'partenaire': forms.Select(attrs={'class': 'form-select'}),
            'periode_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periode_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_echeance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'montant_attendu': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }