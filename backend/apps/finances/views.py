from decimal import Decimal

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

    # ==========================================================
    # QUERYSET DE BASE
    # ==========================================================
    qs = Paiement.objects.select_related(
        'partenaire',
        'enregistre_par'
    )

    # ==========================================================
    # RECHERCHE
    # ==========================================================
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) |
            Q(partenaire__code_partenaire__icontains=q) |
            Q(partenaire__nom__icontains=q) |
            Q(partenaire__prenom__icontains=q)
        )

    # ==========================================================
    # FILTRE STATUT
    # ==========================================================
    if statut:
        qs = qs.filter(statut=statut)

    # ==========================================================
    # FILTRE MODE DE PAIEMENT
    # ==========================================================
    if mode:
        qs = qs.filter(mode_paiement=mode)

    # ==========================================================
    # FILTRE DATE DEBUT
    # ==========================================================
    if date_debut:
        qs = qs.filter(date_paiement__gte=date_debut)

    # ==========================================================
    # FILTRE DATE FIN
    # ==========================================================
    if date_fin:
        qs = qs.filter(date_paiement__lte=date_fin)

    # ==========================================================
    # TOTAL USD
    # ==========================================================
    total_usd = (
        qs.filter(
            statut=StatutPaiement.ACTIF,
            devise='USD'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or Decimal('0')
    )

    # ==========================================================
    # TOTAL CDF
    # ==========================================================
    total_cdf = (
        qs.filter(
            statut=StatutPaiement.ACTIF,
            devise='CDF'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or Decimal('0')
    )

    # ==========================================================
    # NOMBRE DE PAIEMENTS ACTIFS
    # ==========================================================
    nombre_paiements = qs.filter(
        statut=StatutPaiement.ACTIF
    ).count()

    # ==========================================================
    # MOYENNE USD
    # ==========================================================
    if total_usd and qs.filter(
        statut=StatutPaiement.ACTIF,
        devise='USD'
    ).exists():

        nombre_usd = qs.filter(
            statut=StatutPaiement.ACTIF,
            devise='USD'
        ).count()

        moyenne_usd = total_usd / nombre_usd
    else:
        moyenne_usd = Decimal('0')

    # ==========================================================
    # MOYENNE CDF
    # ==========================================================
    if total_cdf and qs.filter(
        statut=StatutPaiement.ACTIF,
        devise='CDF'
    ).exists():

        nombre_cdf = qs.filter(
            statut=StatutPaiement.ACTIF,
            devise='CDF'
        ).count()

        moyenne_cdf = total_cdf / nombre_cdf
    else:
        moyenne_cdf = Decimal('0')

    # ==========================================================
    # PAGINATION
    # ==========================================================
    paginator = Paginator(qs.order_by('-date_paiement', '-created_at'), 20)

    page = paginator.get_page(
        request.GET.get('page')
    )

    # ==========================================================
    # CONTEXTE
    # ==========================================================
    context = {
        'page_obj': page,

        # Filtres
        'q': q,
        'statut': statut,
        'mode': mode,
        'date_debut': date_debut,
        'date_fin': date_fin,

        # Totaux
        'total_usd': total_usd,
        'total_cdf': total_cdf,

        # Statistiques
        'nombre_paiements': nombre_paiements,
        'moyenne_usd': moyenne_usd,
        'moyenne_cdf': moyenne_cdf,

        # Ancienne variable conservée
        # pour éviter de casser un éventuel autre élément du template
        'total': total_usd,
    }

    return render(
        request,
        'finances/paiements_liste.html',
        context
    )


@user_passes_test(peut_gerer_finances)
def paiement_create(request):
    initial = {}

    partenaire_id = request.GET.get('partenaire')

    if partenaire_id:
        initial['partenaire'] = partenaire_id

    form = PaiementForm(
        request.POST or None,
        initial=initial
    )

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

        log_action(
            request.user,
            'CREATE',
            'PAIEMENT',
            paiement.id,
            f"Paiement {paiement.reference} - "
            f"{paiement.montant} {paiement.devise}"
        )

        messages.success(
            request,
            f"Paiement {paiement.reference} enregistré."
        )

        return redirect(
            'finances:paiement_detail',
            pk=paiement.pk
        )

    return render(
        request,
        'finances/paiement_form.html',
        {
            'form': form,
            'titre': 'Nouveau paiement',
            'partenaires': form.fields['partenaire'].queryset,
        }
    )


@login_required
def paiement_detail(request, pk):

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            'partenaire',
            'enregistre_par'
        ),
        pk=pk
    )

    return render(
        request,
        'finances/paiement_detail.html',
        {
            'paiement': paiement
        }
    )


@user_passes_test(peut_gerer_finances)
def paiement_annuler(request, pk):

    paiement = get_object_or_404(
        Paiement,
        pk=pk
    )

    if request.method == 'POST':

        if paiement.statut == StatutPaiement.ANNULE:
            messages.warning(
                request,
                "Ce paiement est déjà annulé."
            )

            return redirect(
                'finances:paiement_detail',
                pk=paiement.pk
            )

        paiement.statut = StatutPaiement.ANNULE

        paiement.save(
            update_fields=[
                'statut',
                'updated_at'
            ]
        )

        # Recalculer les contributions
        for c in ContributionAttendue.objects.filter(
            partenaire=paiement.partenaire
        ):
            c.recalculer()

        log_action(
            request.user,
            'CANCEL',
            'PAIEMENT',
            paiement.id,
            f"Annulation paiement {paiement.reference}"
        )

        messages.warning(
            request,
            f"Paiement {paiement.reference} annulé."
        )

    return redirect(
        'finances:paiement_detail',
        pk=paiement.pk
    )


@login_required
def situation_financiere(request):
    """
    Vue globale des contributions en retard.
    """

    today = timezone.now().date()

    en_retard = ContributionAttendue.objects.filter(
        date_echeance__lt=today,
        statut__in=[
            'EN_ATTENTE',
            'PARTIEL',
            'EN_RETARD'
        ]
    ).select_related(
        'partenaire'
    ).order_by(
        'date_echeance'
    )

    return render(
        request,
        'finances/situation.html',
        {
            'contributions': en_retard,
            'total_retard': en_retard.aggregate(
                t=Sum('solde')
            )['t'] or Decimal('0'),
        }
    )