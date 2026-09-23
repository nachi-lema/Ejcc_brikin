from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.partenaires.models import Partenaire, StatutPartenaire
from apps.finances.models import Paiement, ContributionAttendue, StatutPaiement


def _bornes_periode(debut, fin):
    return debut, fin


@login_required
def dashboard(request):
    today = timezone.now().date()
    debut_mois = today.replace(day=1)
    debut_trimestre = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    debut_annee = date(today.year, 1, 1)

    qs_actifs = Paiement.objects.filter(statut=StatutPaiement.ACTIF)

    stats = {
        'total_partenaires': Partenaire.objects.count(),
        'partenaires_actifs': Partenaire.objects.filter(statut=StatutPartenaire.ACTIF).count(),
        'partenaires_desactives': Partenaire.objects.filter(statut=StatutPartenaire.DESACTIVE).count(),
        'encaisse_jour': qs_actifs.filter(date_paiement=today).aggregate(t=Sum('montant'))['t'] or 0,
        'encaisse_mois': qs_actifs.filter(date_paiement__gte=debut_mois).aggregate(t=Sum('montant'))['t'] or 0,
        'encaisse_trimestre': qs_actifs.filter(date_paiement__gte=debut_trimestre).aggregate(t=Sum('montant'))['t'] or 0,
        'encaisse_annee': qs_actifs.filter(date_paiement__gte=debut_annee).aggregate(t=Sum('montant'))['t'] or 0,
        'total_attendu': ContributionAttendue.objects.exclude(statut='ANNULE').aggregate(t=Sum('montant_attendu'))['t'] or 0,
        'total_paye': qs_actifs.aggregate(t=Sum('montant'))['t'] or 0,
    }
    stats['solde_total'] = stats['total_attendu'] - stats['total_paye']

    stats['partenaires_en_retard'] = ContributionAttendue.objects.filter(
        date_echeance__lt=today,
        statut__in=['EN_ATTENTE', 'PARTIEL', 'EN_RETARD']
    ).values('partenaire').distinct().count()

    derniers_paiements = qs_actifs.select_related('partenaire', 'enregistre_par')[:10]

    # Données graphique : 6 derniers mois
    labels, valeurs = [], []
    for i in range(5, -1, -1):
        d = (debut_mois - timedelta(days=1)).replace(day=1)
        # reculer proprement
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        debut = date(y, m, 1)
        if m == 12:
            fin = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            fin = date(y, m + 1, 1) - timedelta(days=1)
        total = qs_actifs.filter(date_paiement__gte=debut, date_paiement__lte=fin).aggregate(t=Sum('montant'))['t'] or 0
        labels.append(debut.strftime('%b %Y'))
        valeurs.append(float(total))

    return render(request, 'rapports/dashboard.html', {
        'stats': stats,
        'derniers_paiements': derniers_paiements,
        'chart_labels': labels,
        'chart_values': valeurs,
    })


@login_required
def rapport_mensuel(request):
    today = timezone.now().date()
    try:
        annee = int(request.GET.get('annee', today.year))
        mois = int(request.GET.get('mois', today.month))
    except ValueError:
        annee, mois = today.year, today.month

    debut = date(annee, mois, 1)
    fin = (date(annee, mois + 1, 1) - timedelta(days=1)) if mois < 12 else date(annee, 12, 31)

    paiements = Paiement.objects.filter(
        statut=StatutPaiement.ACTIF, date_paiement__gte=debut, date_paiement__lte=fin
    ).select_related('partenaire')

    total = paiements.aggregate(t=Sum('montant'))['t'] or 0
    par_mode = paiements.values('mode_paiement').annotate(total=Sum('montant')).order_by('-total')
    partenaires_payeurs = paiements.values('partenaire').distinct().count()

    context = {
        'annee': annee, 'mois': mois, 'debut': debut, 'fin': fin,
        'paiements': paiements, 'total': total, 'par_mode': par_mode,
        'partenaires_payeurs': partenaires_payeurs,
        'nb_paiements': paiements.count(),
    }
    return render(request, 'rapports/rapport_mensuel.html', context)


@login_required
def rapport_trimestriel(request):
    today = timezone.now().date()
    try:
        annee = int(request.GET.get('annee', today.year))
        trimestre = int(request.GET.get('trimestre', ((today.month - 1) // 3) + 1))
    except ValueError:
        annee, trimestre = today.year, 1

    mois_debut = (trimestre - 1) * 3 + 1
    debut = date(annee, mois_debut, 1)
    mois_fin = mois_debut + 2
    fin = (date(annee, mois_fin + 1, 1) - timedelta(days=1)) if mois_fin < 12 else date(annee, 12, 31)

    paiements = Paiement.objects.filter(
        statut=StatutPaiement.ACTIF, date_paiement__gte=debut, date_paiement__lte=fin
    )

    # Vue par mois
    par_mois = []
    for m in range(mois_debut, mois_fin + 1):
        d = date(annee, m, 1)
        f = (date(annee, m + 1, 1) - timedelta(days=1)) if m < 12 else date(annee, 12, 31)
        total = paiements.filter(date_paiement__gte=d, date_paiement__lte=f).aggregate(t=Sum('montant'))['t'] or 0
        par_mois.append({'mois': d.strftime('%B %Y'), 'total': total})

    return render(request, 'rapports/rapport_trimestriel.html', {
        'annee': annee, 'trimestre': trimestre, 'debut': debut, 'fin': fin,
        'paiements': paiements, 'total': paiements.aggregate(t=Sum('montant'))['t'] or 0,
        'par_mois': par_mois, 'nb_paiements': paiements.count(),
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
    )

    par_mois = []
    for m in range(1, 13):
        d = date(annee, m, 1)
        f = (date(annee, m + 1, 1) - timedelta(days=1)) if m < 12 else date(annee, 12, 31)
        total = paiements.filter(date_paiement__gte=d, date_paiement__lte=f).aggregate(t=Sum('montant'))['t'] or 0
        par_mois.append({'mois': d.strftime('%B'), 'total': total})

    total = paiements.aggregate(t=Sum('montant'))['t'] or 0
    par_mode = paiements.values('mode_paiement').annotate(total=Sum('montant')).order_by('-total')

    return render(request, 'rapports/rapport_annuel.html', {
        'annee': annee, 'debut': debut, 'fin': fin,
        'paiements': paiements, 'total': total, 'moyenne_mensuelle': total / 12 if total else 0,
        'par_mois': par_mois, 'par_mode': par_mode, 'nb_paiements': paiements.count(),
    })


@login_required
def rapport_partenaire(request, pk):
    from apps.partenaires.models import Partenaire
    from django.shortcuts import get_object_or_404
    partenaire = get_object_or_404(Partenaire, pk=pk)
    paiements = partenaire.paiements.filter(statut=StatutPaiement.ACTIF).order_by('-date_paiement')
    contributions = partenaire.contributions_attendues.order_by('-periode_debut')

    total_attendu = contributions.exclude(statut='ANNULE').aggregate(t=Sum('montant_attendu'))['t'] or 0
    total_paye = paiements.aggregate(t=Sum('montant'))['t'] or 0

    return render(request, 'rapports/rapport_partenaire.html', {
        'partenaire': partenaire, 'paiements': paiements,
        'contributions': contributions,
        'total_attendu': total_attendu, 'total_paye': total_paye,
        'solde': total_attendu - total_paye,
    })