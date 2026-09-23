from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import Historique


@user_passes_test(lambda u: u.is_authenticated and u.is_admin)
def liste(request):
    qs = Historique.objects.select_related('utilisateur')
    module = request.GET.get('module', '')
    action = request.GET.get('action', '')
    if module:
        qs = qs.filter(module=module)
    if action:
        qs = qs.filter(action=action)
    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'historique/liste.html', {'page_obj': page})