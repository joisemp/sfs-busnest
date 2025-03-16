from django.urls import path
from services.views import institution_admin
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from services.models import ExportedFile

app_name = 'institution_admin'


urlpatterns = [
     path('registrations/', institution_admin.RegistrationListView.as_view(), name='registration_list'),
     
     path('registrations/<slug:registration_slug>/tickets/', institution_admin.TicketListView.as_view(), name='ticket_list'),
     path('registrations/<slug:registration_slug>/tickets/<slug:ticket_slug>/', institution_admin.TicketUpdateView.as_view(), name='ticket_update'),
     path('registrations/<slug:registration_slug>/tickets/<slug:ticket_slug>/delete/', institution_admin.TicketDeleteView.as_view(), name='ticket_delete'),
     
     path('registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/', institution_admin.BusSearchFormView.as_view(), name='bus_search'),
     # path('registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/available-buses/', institution_admin.BusSearchResultsView.as_view(), name='bus_search_results'),
     
     path('change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-stop/', institution_admin.StopSelectFormView.as_view(), name='stop_select'),
     path('change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-schedule/', institution_admin.SelectScheduleGroupView.as_view(), name='schedule_group_select'),
     path('change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-bus/update-ticket/', institution_admin.BusSearchResultsView.as_view(), name='bus_search_results'),
     path('change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-bus/<slug:bus_slug>/update-ticket/', institution_admin.UpdateBusInfoView.as_view(), name='update_bus_info'),
     
     path('registrations/<slug:registration_slug>/bus-requests/', institution_admin.BusRequestListView.as_view(), name='bus_request_list'),
     path('registrations/<slug:registration_slug>/bus-requests/open/', institution_admin.BusRequestOpenListView.as_view(), name='bus_request_open_list'),
     path('registrations/<slug:registration_slug>/bus-requests/closed/', institution_admin.BusRequestClosedListView.as_view(), name='bus_request_closed_list'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/delete/', institution_admin.BusRequestDeleteView.as_view(), name='bus_request_delete'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/status/', institution_admin.BusRequestStatusUpdateView.as_view(), name='bus_request_status_update'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/comment/', institution_admin.BusRequestCommentView.as_view(), name='bus_request_comment'),
     
     path('registrations/<slug:registration_slug>/receipts/', institution_admin.ReceiptListView.as_view(), name='receipt_list'),
     path('registrations/<slug:registration_slug>/receipts/upload/', institution_admin.ReceiptDataFileUploadView.as_view(), name='receipt_data_file_upload'),
     path('registrations/<slug:registration_slug>/receipts/add/', institution_admin.ReceiptCreateView.as_view(), name='receipt_create'),
     path('registrations/<slug:registration_slug>/receipts/<slug:receipt_slug>/delete/', institution_admin.ReceiptDeleteView.as_view(), name='receipt_delete'),
     
     path('registrations/<slug:registration_slug>/student-groups/', institution_admin.StudentGroupListView.as_view(), name='student_group_list'),
     path('registrations/<slug:registration_slug>/student-groups/create/', institution_admin.StudentGroupCreateView.as_view(), name='student_group_create'),
     path('registrations/<slug:registration_slug>/student-groups/<slug:student_group_slug>/update/', institution_admin.StudentGroupUpdateView.as_view(), name='student_group_update'),
     path('registrations/<slug:registration_slug>/student-groups/<slug:student_group_slug>/delete/', institution_admin.StudentGroupDeleteView.as_view(), name='student_group_delete'),
     
     path('export/<slug:registration_slug>/', institution_admin.TicketExportView.as_view(), name='ticket_export'),
]