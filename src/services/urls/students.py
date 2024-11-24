from django.urls import path
from services.views import students

app_name = 'students'


urlpatterns = [
     path('search-bus/<str:registration_code>/', students.BusSearchFormView.as_view(), name='bus_search'),
     path('bus-results/<str:registration_code>/', students.BusSearchResultsView.as_view(), name='bus_search_results'),
     path('book/<slug:bus_slug>/<str:registration_code>/validate-student/', students.ValidateStudentFormView.as_view(), name='validate_student'),
     path('book/<slug:bus_slug>/<str:registration_code>/', students.BusBookingView.as_view(), name='book_bus'),

]