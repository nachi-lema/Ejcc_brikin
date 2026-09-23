from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Utilisateur, Role
from .forms import LoginForm, UtilisateurForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('rapports:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Bienvenue {user.get_full_name() or user.username} !")
        return redirect('rapports:dashboard')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('accounts:login')


@login_required
def profil_view(request):
    return render(request, 'accounts/profil.html', {'user': request.user})


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin)(view_func)


@admin_required
def utilisateurs_list(request):
    q = request.GET.get('q', '')
    qs = Utilisateur.objects.all()
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/utilisateurs_list.html', {'page_obj': page, 'q': q})


@admin_required
def utilisateur_create(request):
    form = UtilisateurForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f"Utilisateur {user.username} créé.")
        return redirect('accounts:utilisateurs_list')
    return render(request, 'accounts/utilisateur_form.html', {'form': form, 'titre': 'Nouvel utilisateur'})


@admin_required
def utilisateur_update(request, pk):
    user = get_object_or_404(Utilisateur, pk=pk)
    form = UtilisateurForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Utilisateur modifié.")
        return redirect('accounts:utilisateurs_list')
    return render(request, 'accounts/utilisateur_form.html', {'form': form, 'titre': 'Modifier utilisateur', 'user_obj': user})


@admin_required
def utilisateur_toggle(request, pk):
    user = get_object_or_404(Utilisateur, pk=pk)
    if user == request.user:
        messages.error(request, "Vous ne pouvez pas vous désactiver vous-même.")
        return redirect('accounts:utilisateurs_list')
    user.is_active = not user.is_active
    user.save()
    messages.success(request, f"Utilisateur {'activé' if user.is_active else 'désactivé'}.")
    return redirect('accounts:utilisateurs_list')