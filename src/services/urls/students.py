from django.urls import path
from services.views import students

app_name = 'students'


urlpatterns = [
     path('<str:registration_code>/', students.ValidateStudentFormView.as_view(), name='validate_student'),
     path('search-bus/<str:registration_code>/', students.BusSearchFormView.as_view(), name='bus_search'),
     path('bus-results/<str:registration_code>/', students.BusSearchResultsView.as_view(), name='bus_search_results'),
     path('bus-results/<str:registration_code>/not-found/', students.BusNotFoundView.as_view(), name='bus_not_found'),
     path('book/<slug:bus_slug>/<str:registration_code>/', students.BusBookingView.as_view(), name='book_bus'),
     path('book/success/', students.BusBookingSuccessView.as_view(), name='book_success'),

]