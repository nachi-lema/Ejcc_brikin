from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from apps.partenaires.models import Partenaire, StatutPartenaire
from apps.finances.models import Paiement, ContributionAttendue, StatutPaiement


def _somme(qs, devise):
    """Somme filtrée par devise."""
    return qs.filter(devise=devise).aggregate(t=Sum('montant'))['t'] or Decimal('0')


def _somme_attendue(qs, devise):
    """Somme des contributions attendues filtrées par devise du partenaire."""
    return qs.filter(partenaire__devise=devise).exclude(
        statut='ANNULE'
    ).aggregate(t=Sum('montant_attendu'))['t'] or Decimal('0')


@login_required
def dashboard(request):
    today = timezone.now().date()
    debut_mois = today.replace(day=1)
    debut_trimestre = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    debut_annee = date(today.year, 1, 1)

    qs_actifs = Paiement.objects.filter(statut=StatutPaiement.ACTIF)

    # ===== KPI globaux (toutes devises) =====
    stats = {
        'total_partenaires': Partenaire.objects.count(),
        'partenaires_actifs': Partenaire.objects.filter(statut=StatutPartenaire.ACTIF).count(),
        'partenaires_desactives': Partenaire.objects.filter(statut=StatutPartenaire.DESACTIVE).count(),
    }

    stats['partenaires_en_retard'] = ContributionAttendue.objects.filter(
        date_echeance__lt=today,
        statut__in=['EN_ATTENTE', 'PARTIEL', 'EN_RETARD']
    ).values('partenaire').distinct().count()

    # ===== Séparation USD / CDF =====
    devises = {}

    for devise in ['USD', 'CDF']:
        devises[devise] = {
            'jour': _somme(qs_actifs.filter(date_paiement=today), devise),
            'mois': _somme(qs_actifs.filter(date_paiement__gte=debut_mois), devise),
            'trimestre': _somme(qs_actifs.filter(date_paiement__gte=debut_trimestre), devise),
            'annee': _somme(qs_actifs.filter(date_paiement__gte=debut_annee), devise),
            'total_paye': _somme(qs_actifs, devise),
            'total_attendu': _somme_attendue(
                ContributionAttendue.objects.all(), devise
            ),
        }
        devises[devise]['solde'] = devises[devise]['total_attendu'] - devises[devise]['total_paye']

    # ===== Derniers paiements =====
    derniers_paiements = qs_actifs.select_related(
        'partenaire', 'enregistre_par'
    ).order_by('-created_at')[:8]

    # ===== Graphique : 6 derniers mois par devise =====
    chart_labels = []
    chart_usd = []
    chart_cdf = []

    for i in range(5, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        debut = date(y, m, 1)
        fin = (date(y, m + 1, 1) - timedelta(days=1)) if m < 12 else date(y, 12, 31)

        chart_labels.append(debut.strftime('%b %Y'))
        chart_usd.append(float(_somme(
            qs_actifs.filter(date_paiement__gte=debut, date_paiement__lte=fin), 'USD'
        )))
        chart_cdf.append(float(_somme(
            qs_actifs.filter(date_paiement__gte=debut, date_paiement__lte=fin), 'CDF'
        )))

    return render(request, 'rapports/dashboard.html', {
        'stats': stats,
        'devises': devises,
        'derniers_paiements': derniers_paiements,
        'chart_labels': chart_labels,
        'chart_usd': chart_usd,
        'chart_cdf': chart_cdf,
    })


@login_required
def rapport_mensuel(request):
    today = timezone.now().date()

    try:
        annee = int(request.GET.get('annee', today.year))
        mois = int(request.GET.get('mois', today.month))
    except ValueError:
        annee = today.year
        mois = today.month

    # Sécurisation du mois
    mois = max(1, min(12, mois))

    debut = date(annee, mois, 1)

    # Premier jour du mois suivant
    if mois == 12:
        fin = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        fin = date(annee, mois + 1, 1) - timedelta(days=1)

    # Paiements actifs de la période
    paiements = Paiement.objects.filter(
        statut=StatutPaiement.ACTIF,
        date_paiement__gte=debut,
        date_paiement__lte=fin
    ).select_related(
        'partenaire',
        'enregistre_par'
    )

    # Séparation USD / CDF
    devises = {}

    for devise in ['USD', 'CDF']:
        total = _somme(paiements, devise)

        devises[devise] = {
            'total': total,
            'nb': paiements.filter(devise=devise).count(),
        }

    # Répartition par jour
    par_jour = []

    jour = debut

    while jour <= fin:
        total_usd = _somme(
            paiements.filter(date_paiement=jour),
            'USD'
        )

        total_cdf = _somme(
            paiements.filter(date_paiement=jour),
            'CDF'
        )

        par_jour.append({
            'date': jour,
            'label': jour.strftime('%d/%m'),
            'usd': total_usd,
            'cdf': total_cdf,
        })

        jour += timedelta(days=1)

    # Répartition par mode de paiement
    par_mode = []

    for mode_code, mode_label in Paiement._meta.get_field(
        'mode_paiement'
    ).choices:

        total_usd = _somme(
            paiements.filter(mode_paiement=mode_code),
            'USD'
        )

        total_cdf = _somme(
            paiements.filter(mode_paiement=mode_code),
            'CDF'
        )

        if total_usd or total_cdf:
            par_mode.append({
                'mode': mode_label,
                'usd': total_usd,
                'cdf': total_cdf,
            })

    return render(
        request,
        'rapports/rapport_mensuel.html',
        {
            'annee': annee,
            'mois': mois,
            'debut': debut,
            'fin': fin,
            'paiements': paiements,
            'devises': devises,
            'par_jour': par_jour,
            'par_mode': par_mode,
            'nb_paiements': paiements.count(),
        }
    )


@login_required
def rapport_trimestriel(request):
    today = timezone.now().date()
    try:
        annee = int(request.GET.get('annee', today.year))
        trimestre = int(request.GET.get('trimestre', ((today.month - 1) // 3) + 1))
    except ValueError:
        annee, trimestre = today.year, 1

    trimestre = max(1, min(4, trimestre))

    mois_debut = (trimestre - 1) * 3 + 1
    debut = date(annee, mois_debut, 1)
    mois_fin = mois_debut + 2
    fin = (date(annee, mois_fin + 1, 1) - timedelta(days=1)) if mois_fin < 12 else date(annee, 12, 31)

    paiements = Paiement.objects.filter(
        statut=StatutPaiement.ACTIF, date_paiement__gte=debut, date_paiement__lte=fin
    ).select_related('partenaire', 'enregistre_par')

    # Séparation par devise
    devises = {}
    for devise in ['USD', 'CDF']:
        devises[devise] = {
            'total': _somme(paiements, devise),
            'nb': paiements.filter(devise=devise).count(),
        }

    # Vue par mois et par devise
    par_mois = []
    for m in range(mois_debut, mois_fin + 1):
        d = date(annee, m, 1)
        f = (date(annee, m + 1, 1) - timedelta(days=1)) if m < 12 else date(annee, 12, 31)
        par_mois.append({
            'label': d.strftime('%B %Y'),
            'usd': _somme(paiements.filter(date_paiement__gte=d, date_paiement__lte=f), 'USD'),
            'cdf': _somme(paiements.filter(date_paiement__gte=d, date_paiement__lte=f), 'CDF'),
        })

    # Répartition par mode de paiement
    par_mode = []
    for mode_code, mode_label in Paiement._meta.get_field('mode_paiement').choices:
        total_usd = _somme(paiements.filter(mode_paiement=mode_code), 'USD')
        total_cdf = _somme(paiements.filter(mode_paiement=mode_code), 'CDF')
        if total_usd or total_cdf:
            par_mode.append({
                'mode': mode_label,
                'usd': total_usd,
                'cdf': total_cdf,
            })

    return render(request, 'rapports/rapport_trimestriel.html', {
        'annee': annee,
        'trimestre': trimestre,
        'debut': debut,
        'fin': fin,
        'paiements': paiements,
        'devises': devises,
        'par_mois': par_mois,
        'par_mode': par_mode,
        'nb_paiements': paiements.count(),
    })


@login_required
def rapport_annuel(request):
    today = timezone.now().date()
    try:
        annee = int(request.GET.get('annee', today.year))
    except ValueError:
        annee = today.year

    debut = date(annee, 1, 1)
    fin = date(annee, 12, 31)

    paiements = Paiement.objects.filter(
        statut=StatutPaiement.ACTIF, date_paiement__gte=debut, date_paiement__lte=fin
    ).select_related('partenaire', 'enregistre_par')

    # Séparation par devise
    devises = {}
    for devise in ['USD', 'CDF']:
        total = _somme(paiements, devise)
        devises[devise] = {
            'total': total,
            'moyenne_mensuelle': total / 12 if total else Decimal('0'),
            'nb': paiements.filter(devise=devise).count(),
        }

    # Vue mensuelle par devise
    par_mois = []
    for m in range(1, 13):
        d = date(annee, m, 1)
        f = (date(annee, m + 1, 1) - timedelta(days=1)) if m < 12 else date(annee, 12, 31)
        par_mois.append({
            'label': d.strftime('%B'),
            'usd': _somme(paiements.filter(date_paiement__gte=d, date_paiement__lte=f), 'USD'),
            'cdf': _somme(paiements.filter(date_paiement__gte=d, date_paiement__lte=f), 'CDF'),
        })

    # Répartition par mode
    par_mode = []
    for mode_code, mode_label in Paiement._meta.get_field('mode_paiement').choices:
        total_usd = _somme(paiements.filter(mode_paiement=mode_code), 'USD')
        total_cdf = _somme(paiements.filter(mode_paiement=mode_code), 'CDF')
        if total_usd or total_cdf:
            par_mode.append({
                'mode': mode_label,
                'usd': total_usd,
                'cdf': total_cdf,
            })

    return render(request, 'rapports/rapport_annuel.html', {
        'annee': annee,
        'debut': debut,
        'fin': fin,
        'paiements': paiements,
        'devises': devises,
        'par_mois': par_mois,
        'par_mode': par_mode,
        'nb_paiements': paiements.count(),
    })


@login_required
def rapport_partenaire(request, pk):
    partenaire = Partenaire.objects.get(pk=pk)

    paiements = Paiement.objects.filter(
        partenaire=partenaire,
        statut=StatutPaiement.ACTIF
    ).select_related(
        'partenaire',
        'enregistre_par'
    ).order_by('-date_paiement', '-created_at')

    # Totaux par devise
    devises = {}

    for devise in ['USD', 'CDF']:
        total = _somme(paiements, devise)

        devises[devise] = {
            'total': total,
            'nb': paiements.filter(devise=devise).count(),
        }

    # Total attendu
    contributions_attendues = ContributionAttendue.objects.filter(
        partenaire=partenaire
    ).exclude(
        statut='ANNULE'
    )

    attendus = {}

    for devise in ['USD', 'CDF']:
        montant_attendu = contributions_attendues.filter(
            partenaire__devise=devise
        ).aggregate(
            total=Sum('montant_attendu')
        )['total'] or Decimal('0')

        montant_paye = devises[devise]['total']

        attendus[devise] = {
            'attendu': montant_attendu,
            'paye': montant_paye,
            'solde': montant_attendu - montant_paye,
        }

    return render(
        request,
        'rapports/rapport_partenaire.html',
        {
            'partenaire': partenaire,
            'paiements': paiements,
            'devises': devises,
            'attendus': attendus,
            'nb_paiements': paiements.count(),
        }
    )