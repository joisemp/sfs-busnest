from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from services.models import Registration


class CentralAdminOnlyAccessMixin(AccessMixin):
    """
    CentralAdminOnlyAccessMixin is a Django mixin that restricts access to views 
    to only users who are authenticated and have a profile marked as a central admin.
    Methods:
        dispatch(request, *args, **kwargs):
            Overrides the default dispatch method to enforce access control. 
            - If the user is not authenticated, it redirects to the login page or denies access.
            - If the user does not have an associated profile, it raises a 404 error.
            - If the user's profile does not indicate central admin privileges, it raises a 404 error.
            - Otherwise, it allows the request to proceed by calling the parent class's dispatch method.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated: 
            return self.handle_no_permission()  

        if not getattr(request.user, "profile", None): 
            raise Http404("User profile not found.")

        if not request.user.profile.is_central_admin: 
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)


class InsitutionAdminOnlyAccessMixin(AccessMixin):
    """
    InsitutionAdminOnlyAccessMixin is a Django mixin that restricts access to views 
    for users who are not institution administrators.
    Methods:
        dispatch(request, *args, **kwargs):
            Overrides the default dispatch method to enforce access control. 
            - Redirects to the login page or denies access if the user is not authenticated.
            - Raises a 404 error if the user does not have a profile.
            - Raises a 404 error if the user is not an institution administrator.
    Raises:
        Http404: If the user does not have a profile or is not an institution administrator.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:  # If user is not authenticated
            return self.handle_no_permission()  # Redirect to login page or deny access

        if not getattr(request.user, "profile", None):  # Ensure user has a profile
            raise Http404("User profile not found.")

        if not request.user.profile.is_institution_admin:  # Check if user is a central admin
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)


class DriverOnlyAccessMixin(AccessMixin):
    """
    Mixin that restricts access to views to only users who are authenticated and have a driver role.
    
    Methods:
        dispatch(request, *args, **kwargs):
            Overrides the default dispatch method to enforce access control.
            - If the user is not authenticated, it redirects to the login page or denies access.
            - If the user does not have an associated profile, it raises a 404 error.
            - If the user's profile is not a driver, it raises a 404 error.
            - Otherwise, it allows the request to proceed.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, "profile", None):
            raise Http404("User profile not found.")

        if not request.user.profile.is_driver:
            raise Http404("You are not authorized to view this page.")

        return super().dispatch(request, *args, **kwargs)
    

class RedirectLoggedInUsersMixin(AccessMixin):
    """
    A mixin to redirect logged-in users based on their profile type.
    This mixin overrides the `dispatch` method to check if the user is authenticated.
    If the user is authenticated, it verifies the existence of a user profile and redirects
    them to the appropriate page based on their profile type.
    Raises:
        Http404: If the authenticated user does not have an associated profile.
    Redirects:
        - Central Admin users to the 'central_admin:dashboard' URL.
        - Institution Admin users to the 'institution_admin:registration_list' URL.
        - Driver users to the 'drivers:refueling_list' URL.
    If the user is not authenticated, the request is passed to the parent class's `dispatch` method.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if not getattr(request.user, "profile", None):
                raise Http404("User profile not found.")

            if request.user.profile.is_central_admin:
                return HttpResponsePermanentRedirect(reverse('central_admin:dashboard'))
            if request.user.profile.is_institution_admin:
                return HttpResponsePermanentRedirect(reverse('institution_admin:registration_list'))
            if request.user.profile.is_driver:
                return HttpResponsePermanentRedirect(reverse('drivers:refueling_list'))

        return super().dispatch(request, *args, **kwargs)
    

class RegistrationOpenCheckMixin(AccessMixin):
    """
    A mixin to check if a registration is open before processing a request.

    This mixin overrides the `dispatch` method to ensure that the registration
    associated with the provided `registration_code` is open. If the registration
    is not open, an `Http404` exception is raised.

    Methods:
        dispatch(request, *args, **kwargs):
            Checks the status of the registration associated with the `registration_code`
            from the URL keyword arguments. If the registration is closed, raises an
            `Http404` exception. Otherwise, proceeds with the normal dispatch process.

    Raises:
        Http404: If the registration is not open.

    Usage:
        This mixin can be used in views where access is restricted to open registrations.
    """
    def dispatch(self, request, *args, **kwargs):
        registration_code = kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)
        if not registration.status:
            # Render a template instead of raising 404
            return render(request, "registration_closed.html", {"registration": registration})
        return super().dispatch(request, *args, **kwargs)
    

class RegistrationClosedOnlyAccessMixin(AccessMixin):
    """
    Mixin to allow access to a view only if the registration is closed.
    If the registration is open, renders a template or raises 404.
    Usage: Add this mixin to your view before other mixins.
    """
    def dispatch(self, request, *args, **kwargs):
        registration_code = kwargs.get('registration_code')
        registration_slug = kwargs.get('registration_slug')
        registration = None
        if registration_code:
            registration = get_object_or_404(Registration, code=registration_code)
        elif registration_slug:
            registration = get_object_or_404(Registration, slug=registration_slug)
        if registration and registration.status:
            # Registration is open, deny access
            return render(request, "registration_open.html", {"registration": registration})
        return super().dispatch(request, *args, **kwargs)


class ActiveRegistrationRequiredMixin(AccessMixin):
    """
    Mixin that restricts modification operations to only active registrations.
    
    This mixin checks if the registration associated with the view is active.
    If not, it displays an error message and redirects to the appropriate page.
    
    The mixin looks for registration_slug in URL kwargs and retrieves the registration.
    For views that need modification access (Create, Update, Delete), this ensures
    that institution admins can only modify resources for active registrations.
    
    Usage:
        class MyUpdateView(ActiveRegistrationRequiredMixin, UpdateView):
            ...
    
    Methods:
        dispatch(request, *args, **kwargs):
            Checks if the registration is active before allowing the request to proceed.
            If not active, redirects with an error message.
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Check if registration is active before allowing modifications.
        """
        registration_slug = self.kwargs.get('registration_slug')
        registration = get_object_or_404(Registration, slug=registration_slug)
        
        if not registration.is_active:
            messages.error(request, 'Cannot modify resources for non-active registrations.')
            return redirect('institution_admin:registration_list')
        
        return super().dispatch(request, *args, **kwargs)

