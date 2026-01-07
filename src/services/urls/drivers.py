"""
urls.py - URL configuration for driver views

This module defines the URL patterns for driver-related views including dashboard and other driver features.
"""

from django.urls import path
from services.views import drivers

app_name = 'drivers'

urlpatterns = [
    path('dashboard/', drivers.DriverDashboardView.as_view(), name='dashboard'),
]
