from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Partenaire, StatutPartenaire
from .forms import PartenaireForm
from apps.historique.utils import log_action


def peut_gerer(user):
    return user.is_authenticated and user.peut_gerer_partenaires


@login_required
def liste(request):
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    type_p = request.GET.get('type', '')

    qs = Partenaire.objects.all()
    if q:
        qs = qs.filter(
            Q(code_partenaire__icontains=q) |
            Q(nom__icontains=q) |
            Q(postnom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if type_p:
        qs = qs.filter(type_partenaire=type_p)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'partenaires/liste.html', {
        'page_obj': page, 'q': q, 'statut': statut, 'type_p': type_p,
        'statuts': StatutPartenaire.choices,
    })


@login_required
def detail(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    paiements = partenaire.paiements.select_related('enregistre_par').order_by('-date_paiement')[:20]
    contributions = partenaire.contributions_attendues.order_by('-periode_debut')[:12]
    return render(request, 'partenaires/detail.html', {
        'partenaire': partenaire,
        'paiements': paiements,
        'contributions': contributions,
    })


@user_passes_test(peut_gerer)
def creer(request):
    form = PartenaireForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        partenaire = form.save()
        log_action(request.user, 'CREATE', 'PARTENAIRE', partenaire.id,
                   f"Création partenaire {partenaire.code_partenaire}")
        messages.success(request, f"Partenaire {partenaire.code_partenaire} créé.")
        return redirect('partenaires:detail', pk=partenaire.pk)
    return render(request, 'partenaires/form.html', {'form': form, 'titre': 'Nouveau partenaire'})


@user_passes_test(peut_gerer)
def modifier(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    form = PartenaireForm(request.POST or None, instance=partenaire)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request.user, 'UPDATE', 'PARTENAIRE', partenaire.id,
                   f"Modification partenaire {partenaire.code_partenaire}")
        messages.success(request, "Partenaire modifié.")
        return redirect('partenaires:detail', pk=partenaire.pk)
    return render(request, 'partenaires/form.html', {
        'form': form, 'titre': f'Modifier {partenaire.code_partenaire}', 'partenaire': partenaire
    })


@user_passes_test(peut_gerer)
def desactiver(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    if request.method == 'POST':
        partenaire.desactiver()
        log_action(request.user, 'DEACTIVATE', 'PARTENAIRE', partenaire.id,
                   f"Désactivation {partenaire.code_partenaire}")
        messages.warning(request, f"Partenaire {partenaire.code_partenaire} désactivé.")
    return redirect('partenaires:detail', pk=partenaire.pk)


@user_passes_test(peut_gerer)
def reactiver(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    if request.method == 'POST':
        partenaire.reactiver()
        log_action(request.user, 'REACTIVATE', 'PARTENAIRE', partenaire.id,
                   f"Réactivation {partenaire.code_partenaire}")
        messages.success(request, f"Partenaire {partenaire.code_partenaire} réactivé.")
    return redirect('partenaires:detail', pk=partenaire.pk)


@login_required
def situation(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    contributions = partenaire.contributions_attendues.order_by('-periode_debut')
    return render(request, 'partenaires/situation.html', {
        'partenaire': partenaire, 'contributions': contributions,
    })