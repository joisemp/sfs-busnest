from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
from django.http import Http404
from django.utils import timezone
from django.shortcuts import get_object_or_404
from services.models import Registration


class CentralAdminOnlyAccessMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:  # If user is not authenticated
            return self.handle_no_permission()  # Redirect to login page or deny access

        if not getattr(request.user, "profile", None):  # Ensure user has a profile
            raise Http404("User profile not found.")

        if not request.user.profile.is_central_admin:  # Check if user is a central admin
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)


class InsitutionAdminOnlyAccessMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:  # If user is not authenticated
            return self.handle_no_permission()  # Redirect to login page or deny access

        if not getattr(request.user, "profile", None):  # Ensure user has a profile
            raise Http404("User profile not found.")

        if not request.user.profile.is_institution_admin:  # Check if user is a central admin
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)
    

class RedirectLoggedInUsersMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if not getattr(request.user, "profile", None):
                raise Http404("User profile not found.")

            if request.user.profile.is_central_admin:
                return HttpResponsePermanentRedirect(reverse('central_admin:dashboard'))
            if request.user.profile.is_institution_admin:
                return HttpResponsePermanentRedirect(reverse('institution_admin:registration_list'))

        return super().dispatch(request, *args, **kwargs)
    

class RegistrationOpenCheckMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        registration_code = kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)
        if not registration.status:
            raise Http404("Registration is not open.")
        return super().dispatch(request, *args, **kwargs)
        
        