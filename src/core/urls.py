from django.urls import path
"""
URL configuration for the 'core' app.
Defines URL patterns for authentication, password management, and notification-related views.
URL Patterns:
- 'login/': User login view.
- 'register/': User registration view.
- 'logout/': User logout view.
- 'change-password/': View for changing user password.
- 'reset-password/': Initiate password reset process.
- 'done-password-reset/': Confirmation view after password reset request.
- 'confirm-password-reset/<uidb64>/<token>/': Confirm password reset with user ID and token.
- 'complete-password-reset/': Complete the password reset process.
- 'priority-notifications/': View to retrieve priority notifications.
- 'notifications/<int:notification_id>/read/': Mark a specific notification as read.
- 'notifications/': List all notifications for the user.
All views are imported from the 'core.views' module.
The app namespace is set to 'core' for namespacing URL names.
"""
from core import views
from .views import priority_notifications_view, mark_notification_as_read

app_name = 'core'

urlpatterns = [
     path('login/', views.LoginView.as_view(), name='login'),
     path('register/', views.UserRegisterView.as_view(), name='register'),
     path('logout/', views.LogoutView.as_view(), name='logout'),
     path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
     path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
     path('done-password-reset/', views.DonePasswordResetView.as_view(),
          name='done_password_reset'),
     path('confirm-password-reset/<uidb64>/<token>/',
          views.ConfirmPasswordResetView.as_view(), name='confirm_password_reset'),
     path('complete-password-reset/', views.CompletePasswordResetView.as_view(),
          name='complete_password_reset'),
     path('priority-notifications/', priority_notifications_view, name='priority_notifications'),
     path('notifications/<int:notification_id>/read/', mark_notification_as_read, name='mark_notification_as_read'),
     path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
]