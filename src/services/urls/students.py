"""
students.py - URL configuration for student operations in the services app

This module defines URL patterns for student-facing views, including student validation, rules and regulations,
stop and schedule selection, pickup/drop stop and bus selection, bus search results, bus request, and bus booking.

URL Patterns (detailed):
- <str:registration_code>/: Validate student for a registration.
- <str:registration_code>/rules-and-regulations/: View rules and regulations for a registration.
- <str:registration_code>/select-stop/: Select a stop for a registration.
- <str:registration_code>/select-schedule/: Select a schedule group for a registration.
- <str:registration_code>/select-pickup-stop/: Select a pickup stop for a registration.
- <str:registration_code>/select-pickup-bus/: Select a pickup bus for a registration.
- <str:registration_code>/select-drop-stop/: Select a drop stop for a registration.
- <str:registration_code>/select-drop-bus/: Select a drop bus for a registration.
- bus-results/<str:registration_code>/: View bus search results for a registration.
- bus-results/<str:registration_code>/not-found/: View when no bus is found for a registration.
- bus-results/<str:registration_code>/request/: Submit a bus request for a registration.
- bus-results/<str:registration_code>/request/success/: View success page after submitting a bus request.
- book/<str:registration_code>/: Book a bus for a registration.
- book/<str:registration_code>/success/: View success page after booking a bus.
"""

from django.urls import path
from services.views import students

app_name = 'students'


urlpatterns = [
     path('<str:registration_code>/', students.ValidateStudentFormView.as_view(), name='validate_student'),
     path('<str:registration_code>/rules-and-regulations/', students.RulesAndRegulationsView.as_view(), name='rules_and_regulations'),
     path('<str:registration_code>/select-stop/', students.StopSelectFormView.as_view(), name='stop_select'),
     path('<str:registration_code>/select-schedule/', students.SelectScheduleGroupView.as_view(), name='schedule_group_select'),
     
     path('<str:registration_code>/select-pickup-stop/', students.PickupStopSelectFormView.as_view(), name='pickup_stop_select'),
     path('<str:registration_code>/select-pickup-bus/', students.PickupBusSearchResultsView.as_view(), name='pickup_bus_select'),
     path('<str:registration_code>/select-drop-stop/', students.DropStopSelectFormView.as_view(), name='drop_stop_select'),
     path('<str:registration_code>/select-drop-bus/', students.DropBusSearchResultsView.as_view(), name='drop_bus_select'),
     
     path('bus-results/<str:registration_code>/', students.BusSearchResultsView.as_view(), name='bus_search_results'),
     path('bus-results/<str:registration_code>/not-found/', students.BusNotFoundView.as_view(), name='bus_not_found'),
     path('bus-results/<str:registration_code>/request/', students.BusRequestFormView.as_view(), name='bus_request'),
     path('bus-results/<str:registration_code>/request/success/', students.BusRequestSuccessView.as_view(), name='bus_request_success'),
     path('book/<str:registration_code>/', students.BusBookingView.as_view(), name='book_bus'),
     path('book/<str:registration_code>/success/', students.BusBookingSuccessView.as_view(), name='book_success'),

]