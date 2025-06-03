from services.models import Notification

def priority_notifications(request):
    """
    Context processor that provides priority unread notifications for the authenticated user.

    If the user is authenticated, retrieves all notifications associated with the user that are marked as priority and have a status of "unread".
    If the user is not authenticated, returns an empty list.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        dict: A dictionary containing the key 'priority_notifications' mapped to a queryset of priority unread notifications for the user, or an empty list if the user is not authenticated.
    """
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, priority=True, status="unread")
    else:
        notifications = []
    return {'priority_notifications': notifications}