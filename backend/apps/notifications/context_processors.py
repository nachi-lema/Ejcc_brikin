def notifications_count(request):
    if request.user.is_authenticated:
        return {'notifications_non_lues': request.user.notifications.filter(lu=False).count()}
    return {'notifications_non_lues': 0}