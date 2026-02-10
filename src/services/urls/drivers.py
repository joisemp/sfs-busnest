"""
urls.py - URL configuration for driver views

This module defines the URL patterns for driver-related views including trip record management,
refueling record management, and student lists. All driver operations are scoped to their single 
assigned bus in the active registration.
"""

from django.urls import path
from services.views import drivers

app_name = 'drivers'

urlpatterns = [
    # Trip Records (Default)
    path('', drivers.DriverTripRecordListView.as_view(), name='trip_records_list'),
    path('trip-records/', drivers.DriverTripRecordListView.as_view(), name='trip_records_list_alt'),
    path('trip-records/add/', drivers.DriverTripRecordCreateView.as_view(), name='trip_record_create'),
    path('trip-records/<slug:slug>/update/', drivers.DriverTripRecordUpdateView.as_view(), name='trip_record_update'),
    
    # Refueling Records
    path('refueling/', drivers.DriverRefuelingListView.as_view(), name='refueling_list'),
    path('refueling/add/', drivers.DriverRefuelingCreateView.as_view(), name='refueling_create'),
    path('refueling/<slug:slug>/update/', drivers.DriverRefuelingUpdateView.as_view(), name='refueling_update'),
    
    # Students
    path('students/', drivers.DriverStudentsListView.as_view(), name='students_list'),
]
