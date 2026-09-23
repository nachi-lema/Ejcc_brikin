from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def liste(request):
    notifications = request.user.notifications.all()[:100]
    return render(request, 'notifications/liste.html', {'notifications': notifications})


@login_required
def marquer_lu(request, pk):
    n = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    n.lu = True
    n.save(update_fields=['lu'])
    return redirect(n.lien or 'notifications:liste')


@login_required
def tout_marquer_lu(request):
    request.user.notifications.filter(lu=False).update(lu=True)
    return redirect('notifications:liste')