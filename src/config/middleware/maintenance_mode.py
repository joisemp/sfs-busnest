from django.conf import settings
from django.shortcuts import render

class MaintenanceModeMiddleware:
    """
    Middleware to display a maintenance page when MAINTENANCE_MODE is enabled.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Allow superusers to bypass maintenance mode
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)
            return render(request, 'maintenance.html', status=503)
        return self.get_response(request)
