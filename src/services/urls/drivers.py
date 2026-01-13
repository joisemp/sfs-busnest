"""
urls.py - URL configuration for driver views

This module defines the URL patterns for driver-related views including dashboard 
and refueling record management. All driver operations are scoped to their single 
assigned bus in the active registration.
"""

from django.urls import path
from services.views import drivers

app_name = 'drivers'

urlpatterns = [
    path('dashboard/', drivers.DriverDashboardView.as_view(), name='dashboard'),
    path('refueling/', drivers.DriverRefuelingListView.as_view(), name='refueling_list'),
    path('refueling/add/', drivers.DriverRefuelingCreateView.as_view(), name='refueling_create'),
    path('refueling/<slug:slug>/update/', drivers.DriverRefuelingUpdateView.as_view(), name='refueling_update'),
    path('students/', drivers.DriverStudentsListView.as_view(), name='students_list'),
]
