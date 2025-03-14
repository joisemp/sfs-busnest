from services.models import Notification

def priority_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, priority=True, status="unread")
    else:
        notifications = []
    return {'priority_notifications': notifications}