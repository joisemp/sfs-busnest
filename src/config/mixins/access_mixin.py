from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
from django.http import Http404


class CentralAdminOnlyAccessMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:  # If user is not authenticated
            return self.handle_no_permission()  # Redirect to login page or deny access

        if not getattr(request.user, "profile", None):  # Ensure user has a profile
            raise Http404("User profile not found.")

        if not request.user.profile.is_central_admin:  # Check if user is a central admin
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)
    
    