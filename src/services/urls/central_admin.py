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
]