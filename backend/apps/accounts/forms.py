from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Utilisateur, Role


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Nom d\'utilisateur',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d\'utilisateur'})
    )
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )


class UtilisateurForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Laisser vide pour ne pas modifier'
    )
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Utilisateur
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password1')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user