"""
urls.py - URL configuration for mechanic views

This module defines the URL patterns for mechanic-related views including dashboard,
maintenance record management, and bus tracking. All mechanic operations are scoped 
to their organization.
"""

from django.urls import path
from services.views import mechanics

app_name = 'mechanics'

urlpatterns = [
    # Dashboard (Default)
    path('', mechanics.MechanicDashboardView.as_view(), name='dashboard'),
    path('dashboard/', mechanics.MechanicDashboardView.as_view(), name='dashboard_alt'),
]
