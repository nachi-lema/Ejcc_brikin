from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Paiement, ContributionAttendue, StatutPaiement
from .forms import PaiementForm
from apps.partenaires.models import Partenaire
from apps.historique.utils import log_action


def peut_gerer_finances(user):
    return user.is_authenticated and user.peut_gerer_finances


@login_required
def paiements_liste(request):
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    mode = request.GET.get('mode', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    qs = Paiement.objects.select_related('partenaire', 'enregistre_par')
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) |
            Q(partenaire__code_partenaire__icontains=q) |
            Q(partenaire__nom__icontains=q) |
            Q(partenaire__prenom__icontains=q)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if mode:
        qs = qs.filter(mode_paiement=mode)
    if date_debut:
        qs = qs.filter(date_paiement__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_paiement__lte=date_fin)

    total = qs.filter(statut=StatutPaiement.ACTIF).aggregate(t=Sum('montant'))['t'] or 0
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'finances/paiements_liste.html', {
        'page_obj': page, 'q': q, 'statut': statut, 'mode': mode,
        'date_debut': date_debut, 'date_fin': date_fin, 'total': total,
    })


@user_passes_test(peut_gerer_finances)
def paiement_create(request):
    initial = {}
    partenaire_id = request.GET.get('partenaire')
    if partenaire_id:
        initial['partenaire'] = partenaire_id

    form = PaiementForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        paiement = form.save(commit=False)
        paiement.enregistre_par = request.user
        paiement.save()
        # Recalculer les contributions concernées
        contributions = ContributionAttendue.objects.filter(
            partenaire=paiement.partenaire,
            periode_debut__lte=paiement.periode_fin,
            periode_fin__gte=paiement.periode_debut,
        )
        for c in contributions:
            c.recalculer()

        log_action(request.user, 'CREATE', 'PAIEMENT', paiement.id,
                   f"Paiement {paiement.reference} - {paiement.montant} {paiement.devise}")
        messages.success(request, f"Paiement {paiement.reference} enregistré.")
        return redirect('finances:paiement_detail', pk=paiement.pk)
    return render(request, 'finances/paiement_form.html', {
        'form': form,
        'titre': 'Nouveau paiement',
        'partenaires': form.fields['partenaire'].queryset,  # ← pour le widget custom
    })


@login_required
def paiement_detail(request, pk):
    paiement = get_object_or_404(Paiement.objects.select_related('partenaire', 'enregistre_par'), pk=pk)
    return render(request, 'finances/paiement_detail.html', {'paiement': paiement})


@user_passes_test(peut_gerer_finances)
def paiement_annuler(request, pk):
    paiement = get_object_or_404(Paiement, pk=pk)
    if request.method == 'POST':
        if paiement.statut == StatutPaiement.ANNULE:
            messages.warning(request, "Ce paiement est déjà annulé.")
            return redirect('finances:paiement_detail', pk=paiement.pk)
        paiement.statut = StatutPaiement.ANNULE
        paiement.save(update_fields=['statut', 'updated_at'])
        # Recalculer contributions
        for c in ContributionAttendue.objects.filter(partenaire=paiement.partenaire):
            c.recalculer()
        log_action(request.user, 'CANCEL', 'PAIEMENT', paiement.id,
                   f"Annulation paiement {paiement.reference}")
        messages.warning(request, f"Paiement {paiement.reference} annulé.")
    return redirect('finances:paiement_detail', pk=paiement.pk)


@login_required
def situation_financiere(request):
    """Vue globale des contributions en retard"""
    today = timezone.now().date()
    en_retard = ContributionAttendue.objects.filter(
        date_echeance__lt=today,
        statut__in=['EN_ATTENTE', 'PARTIEL', 'EN_RETARD']
    ).select_related('partenaire').order_by('date_echeance')
    return render(request, 'finances/situation.html', {
        'contributions': en_retard,
        'total_retard': en_retard.aggregate(t=Sum('solde'))['t'] or 0,
    })