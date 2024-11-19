from django.urls import path
from services.views import central_admin

app_name = 'central_admin'

urlpatterns = [
     path('institutions/', central_admin.InstitutionListView.as_view(), name='institution_list'),
     path('institutions/create/', central_admin.InstitutionCreateView.as_view(), name='institution_create'),
     path('institutions/<slug:slug>/update/', central_admin.InstitutionUpdateView.as_view(), name='institution_update'),
     path('institutions/<slug:slug>/delete/', central_admin.InstitutionDeleteView.as_view(), name='institution_delete'),
     
     path('buses/', central_admin.BusListView.as_view(), name='bus_list'),
     path('buses/create/', central_admin.BusCreateView.as_view(), name='bus_create'),
     path('buses/<slug:slug>/update/', central_admin.BusUpdateView.as_view(), name='bus_update'),
     path('buses/<slug:slug>/delete/', central_admin.BusDeleteView.as_view(), name='bus_delete'),
     
     path('people/', central_admin.PeopleListView.as_view(), name='people_list'),
     path('people/add/', central_admin.PeopleCreateView.as_view(), name='people_create'),
     path('people/<slug:slug>/update/', central_admin.PeopleUpdateView.as_view(), name='people_update'),
     path('people/<slug:slug>/delete/', central_admin.PeopleDeleteView.as_view(), name='people_delete'),
     
     path('routes/', central_admin.RouteListView.as_view(), name='route_list'),
     path('routes/create/', central_admin.RouteCreateView.as_view(), name='route_create'),
     path('routes/<slug:slug>/update/', central_admin.RouteUpdateView.as_view(), name='route_update'),
     path('routes/<slug:slug>/delete/', central_admin.RouteDeleteView.as_view(), name='route_delete'),
     path('routes/stops/add/', central_admin.StopCreateView.as_view(), name='stop_create'),
     path('routes/stops/<slug:slug>/delete/', central_admin.StopDeleteView.as_view(), name='stop_delete'),
     
     path('registrations/', central_admin.RegistraionListView.as_view(), name='registration_list'),
     path('registrations/create/', central_admin.RegistrationCreateView.as_view(), name='registration_create'),
     path('registrations/<slug:slug>/update/', central_admin.RegistrationUpdateView.as_view(), name='registration_update'),
     path('registrations/<slug:slug>/delete/', central_admin.RegistrationDeleteView.as_view(), name='registration_delete'),
]