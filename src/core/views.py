from django.shortcuts import redirect, render
from django.db import transaction
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, 
    PasswordResetCompleteView, PasswordResetConfirmView, 
    PasswordResetDoneView, PasswordResetView
    )
from django.contrib.auth import login
from django.urls import reverse_lazy
from . forms import CustomAuthenticationForm, UserRegisterForm
from django.views.generic import CreateView
from core.models import UserProfile
from django.contrib.auth import get_user_model
from services.models import Organisation
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

User = get_user_model()


class LoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'core/login.html'

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect('landing_page')
    

class UserRegisterView(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('core:login')
    
    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        
        org_name = form.cleaned_data.get('org_name')
        area = form.cleaned_data.get('area')
        city = form.cleaned_data.get('city')
        org = Organisation.objects.create(
            name = org_name,
            area = area,
            city = city,
        )
        
        # Create user profile
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        UserProfile.objects.create(
            user=user, 
            org = org,
            first_name=first_name, 
            last_name=last_name, 
            is_central_admin=True
            )
        
        login(self.request, user)
        return redirect('landing_page')
    
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'ALLOW_USER_REGISTRATION', True):
            raise PermissionDenied("User registration is disabled.")
        return super().dispatch(request, *args, **kwargs)


class LogoutView(LogoutView):
    template_name = 'core/logout.html'


class ChangePasswordView(PasswordChangeView):
    template_name = 'core/change_password.html'
    success_url = reverse_lazy('landing_page')


class ResetPasswordView(PasswordResetView):
    email_template_name = 'core/password_reset/password_reset_email.html'
    html_email_template_name = 'core/password_reset/password_reset_email.html'
    subject_template_name = 'core/password_reset/password_reset_subject.txt'
    success_url = reverse_lazy('core:done_password_reset')
    template_name = 'core/password_reset/password_reset_form.html'


class DonePasswordResetView(PasswordResetDoneView):
    template_name = 'core/password_reset/password_reset_done.html'


class ConfirmPasswordResetView(PasswordResetConfirmView):
    success_url = reverse_lazy('core:complete_password_reset')
    template_name = 'core/password_reset/password_reset_confirm.html'


class CompletePasswordResetView(PasswordResetCompleteView):
    template_name = 'core/password_reset/password_reset_complete.html'



from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from services.models import Notification

@login_required
def priority_notifications_view(request):
    notifications = Notification.objects.filter(user=request.user, priority=True, status="unread")
    return render(request, 'core/priority_notifications.html', {'priority_notifications': notifications})

@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.status = "read"
    notification.save()

    # Fetch updated priority notifications
    notifications = Notification.objects.filter(user=request.user, priority=True, status="unread")
    return render(request, 'core/priority_notifications.html', {'priority_notifications': notifications})

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'core/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context