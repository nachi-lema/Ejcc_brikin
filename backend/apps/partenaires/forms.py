from django import forms
from .models import Partenaire


class PartenaireForm(forms.ModelForm):
    class Meta:
        model = Partenaire
        fields = ['nom', 'postnom', 'prenom', 'telephone', 'email', 'adresse',
                  'type_partenaire', 'date_adhesion', 'montant_contribution',
                  'frequence', 'devise', 'observation']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'postnom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+243...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'type_partenaire': forms.Select(attrs={'class': 'form-select'}),
            'date_adhesion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'montant_contribution': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'frequence': forms.Select(attrs={'class': 'form-select'}),
            'devise': forms.Select(attrs={'class': 'form-select'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_telephone(self):
        tel = self.cleaned_data.get('telephone', '').strip()
        if len(tel) < 8:
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return tel

    def clean_montant_contribution(self):
        m = self.cleaned_data.get('montant_contribution')
        if m is not None and m < 0:
            raise forms.ValidationError("Le montant ne peut pas être négatif.")
        return m