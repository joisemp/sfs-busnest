from django.urls import path
from services.views import students

app_name = 'students'


urlpatterns = [
     path('search-bus/<str:code>/', students.BusSearchFormView.as_view(), name='bus_search'),
     path('bus-results/<str:code>/', students.BusSearchResultsView.as_view(), name='bus_search_results'),
]