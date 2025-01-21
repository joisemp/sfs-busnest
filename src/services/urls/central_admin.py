from django.urls import path
from services.views import central_admin
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from services.models import ExportedFile

app_name = 'central_admin'

def exported_file_download(request, file_id):
    exported_file = get_object_or_404(ExportedFile, id=file_id)
    return FileResponse(exported_file.file, as_attachment=True, filename='ticket_export.xlsx')

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
     
     path('registrations/', central_admin.RegistraionListView.as_view(), name='registration_list'),
     path('registrations/create/', central_admin.RegistrationCreateView.as_view(), name='registration_create'),
     path('registrations/<slug:registration_slug>/', central_admin.RegistrationDetailView.as_view(), name='registration_detail'),
     path('registrations/<slug:registration_slug>/update/', central_admin.RegistrationUpdateView.as_view(), name='registration_update'),
     path('registrations/<slug:registration_slug>/delete/', central_admin.RegistrationDeleteView.as_view(), name='registration_delete'),
     
     path('registrations/<slug:registration_slug>/routes/', central_admin.RouteListView.as_view(), name='route_list'),
     path('registrations/<slug:registration_slug>/routes/upload/', central_admin.RouteFileUploadView.as_view(), name='route_file_upload'),
     path('registrations/<slug:registration_slug>/routes/create/', central_admin.RouteCreateView.as_view(), name='route_create'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/update/', central_admin.RouteUpdateView.as_view(), name='route_update'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/delete/', central_admin.RouteDeleteView.as_view(), name='route_delete'),
     path('registrations/<slug:registration_slug>/routes/stops/add/', central_admin.StopCreateView.as_view(), name='stop_create'),
     path('registrations/<slug:registration_slug>/routes/stops/<slug:stop_slug>/delete/', central_admin.StopDeleteView.as_view(), name='stop_delete'),
     
     path('registrations/<slug:registration_slug>/faq/create/', central_admin.FAQCreateView.as_view(), name='faq_create'),
     path('registrations/<slug:registration_slug>/faq/<slug:faq_slug>/delete/', central_admin.FAQDeleteView.as_view(), name='faq_delete'),
     
     path('registrations/<slug:registration_slug>/tickets/', central_admin.TicketListView.as_view(), name='ticket_list'),
     
     path('registrations/<slug:registration_slug>/schedules/', central_admin.ScheduleListView.as_view(), name='schedule_list'),
     path('registrations/<slug:registration_slug>/schedules/create/', central_admin.ScheduleCreateView.as_view(), name='schedule_create'),
     path('registrations/<slug:registration_slug>/schedules/<slug:schedule_slug>/update/', central_admin.ScheduleUpdateView.as_view(), name='schedule_update'),
     
     path('registrations/<slug:registration_slug>/bus-records/', central_admin.BusRecordListView.as_view(), name='bus_record_list'),
     
     path('registrations/<slug:registration_slug>/bus-requests/', central_admin.BusRequestListView.as_view(), name='bus_request_list'),
     
     path('more/', central_admin.MoreMenuView.as_view(), name='more_menu'),
     
     path('export/<slug:registration_slug>/', central_admin.TicketExportView.as_view(), name='ticket_export'),
     path('exported-file/<int:file_id>/', exported_file_download, name='exported_file_download'),

]