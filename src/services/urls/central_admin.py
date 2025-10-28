"""
central_admin.py - URL configuration for central admin operations in the services app

This module defines URL patterns for central admin views, including dashboards, institution management,
bus management, people management, registrations, routes, stops, FAQs, tickets, schedules, schedule groups,
bus records, trips, bus searches, bus requests, student group filtering, file exports, and student pass generation.

Functions:
- exported_file_download: Handles file download for exported files by slug.

URL Patterns (detailed):
- dashboard/: Central admin dashboard view.
- institutions/: List all institutions.
- institutions/create/: Create a new institution.
- institutions/<slug:slug>/update/: Update an institution.
- institutions/<slug:slug>/delete/: Delete an institution.
- buses/: List all buses.
- buses/upload/: Upload buses in bulk via file.
- buses/create/: Create a new bus.
- buses/<slug:slug>/update/: Update a bus.
- buses/<slug:slug>/delete/: Delete a bus.
- people/: List all people (users).
- people/add/: Add a new person.
- people/<slug:slug>/update/: Update a person.
- people/<slug:slug>/delete/: Delete a person.
- registrations/: List all registrations.
- registrations/create/: Create a new registration.
- registrations/<slug:registration_slug>/: Registration details view.
- registrations/<slug:registration_slug>/update/: Update a registration.
- registrations/<slug:registration_slug>/delete/: Delete a registration.
- registrations/<slug:registration_slug>/routes/: List all routes for a registration.
- registrations/<slug:registration_slug>/routes/upload/: Upload routes in bulk via file.
- registrations/<slug:registration_slug>/routes/create/: Create a new route.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/update/: Update a route.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/delete/: Delete a route.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/add/: Add a stop to a route.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/: List all stops for a route.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/update/: Update a stop.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/delete/: Delete a stop.
- registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/transfer/: Transfer a stop (form-based).
- registrations/<slug:registration_slug>/stops/transfer-management/: Drag-and-drop stop transfer interface.
- registrations/<slug:registration_slug>/stops/transfer-api/: API endpoint for stop transfer operations.
- registrations/<slug:registration_slug>/stops/update-name-api/: API endpoint for updating stop names inline.
- registrations/<slug:registration_slug>/faq/create/: Create a new FAQ for a registration.
- registrations/<slug:registration_slug>/faq/<slug:faq_slug>/delete/: Delete an FAQ.
- registrations/<slug:registration_slug>/tickets/: List all tickets for a registration.
- registrations/<slug:registration_slug>/tickets/export/: Export tickets for a registration.
- registrations/<slug:registration_slug>/tickets/filter/: Filter tickets for a registration.
- registrations/<slug:registration_slug>/schedules/: List all schedules for a registration.
- registrations/<slug:registration_slug>/schedules/create/: Create a new schedule.
- registrations/<slug:registration_slug>/schedules/<slug:schedule_slug>/update/: Update a schedule.
- registrations/<slug:registration_slug>/schedule-groups/: List all schedule groups for a registration.
- registrations/<slug:registration_slug>/schedule-groups/create/: Create a new schedule group.
- registrations/<slug:registration_slug>/bus-records/: List all bus records for a registration.
- registrations/<slug:registration_slug>/bus-records/create/: Create a new bus record.
- registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/update/: Update a bus record.
- registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/: List all trips for a bus record.
- registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/create/: Create a new trip.
- registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/<slug:trip_slug>/delete/: Delete a trip.
- registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/: Search for available buses for a ticket.
- registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/available-buses/: Show available buses for a ticket.
- registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/select-bus/<slug:bus_record_slug>/update-ticket/: Update a ticket with the selected bus.
- registrations/<slug:registration_slug>/bus-requests/: List all bus requests for a registration.
- registrations/<slug:registration_slug>/bus-requests/open/: List open bus requests.
- registrations/<slug:registration_slug>/bus-requests/closed/: List closed bus requests.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/delete/: Delete a bus request.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/status/: Update the status of a bus request.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/comment/: Add a comment to a bus request.
- registrations/student-groups/filter/: Filter student groups.
- more/: Show the "more" menu for central admin.
- exported-file/<slug:slug>/: Download an exported file.
- registrations/<slug:registration_slug>/generate-student-pass/: Generate student passes for a registration.
- student-pass/download/<slug:slug>/: Download a generated student pass file.
"""

from django.urls import path
from services.views import central_admin
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from services.models import ExportedFile
from services.views.central_admin import GenerateStudentPassView, StudentPassFileDownloadView, ReservationListView,ReservationDetailView

app_name = 'central_admin'

def exported_file_download(request, slug):
    exported_file = get_object_or_404(ExportedFile, slug=slug)
    return FileResponse(exported_file.file, as_attachment=True, filename='ticket_export.xlsx')

urlpatterns = [
    path('dashboard/', central_admin.DashboardView.as_view(), name='dashboard'),
    
     path('institutions/', central_admin.InstitutionListView.as_view(), name='institution_list'),
     path('institutions/create/', central_admin.InstitutionCreateView.as_view(), name='institution_create'),
     path('institutions/<slug:slug>/update/', central_admin.InstitutionUpdateView.as_view(), name='institution_update'),
     path('institutions/<slug:slug>/delete/', central_admin.InstitutionDeleteView.as_view(), name='institution_delete'),
     
     path('buses/', central_admin.BusListView.as_view(), name='bus_list'),
     path('buses/upload/', central_admin.BusFileUploadView.as_view(), name='bus_upload'),
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
     
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/add/', central_admin.StopCreateView.as_view(), name='stop_create'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/', central_admin.StopListView.as_view(), name='stop_list'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/update/', central_admin.StopUpdateView.as_view(), name='stop_update'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/delete/', central_admin.StopDeleteView.as_view(), name='stop_delete'),
     path('registrations/<slug:registration_slug>/routes/<slug:route_slug>/stops/<slug:stop_slug>/transfer/', central_admin.StopTransferView.as_view(), name='stop_transfer'),
     
     # Drag-and-drop stop transfer management
     path('registrations/<slug:registration_slug>/stops/transfer-management/', central_admin.StopTransferManagementView.as_view(), name='stop_transfer_management'),
     path('registrations/<slug:registration_slug>/stops/transfer-api/', central_admin.TransferStopAPIView.as_view(), name='transfer_stop_api'),
     path('registrations/<slug:registration_slug>/stops/update-name-api/', central_admin.UpdateStopNameAPIView.as_view(), name='update_stop_name_api'),
     
     path('registrations/<slug:registration_slug>/faq/create/', central_admin.FAQCreateView.as_view(), name='faq_create'),
     path('registrations/<slug:registration_slug>/faq/<slug:faq_slug>/delete/', central_admin.FAQDeleteView.as_view(), name='faq_delete'),
     
     path('registrations/<slug:registration_slug>/tickets/', central_admin.TicketListView.as_view(), name='ticket_list'),
     path('registrations/<slug:registration_slug>/tickets/export/', central_admin.TicketExportView.as_view(), name='ticket_export'),
     path('registrations/<slug:registration_slug>/tickets/filter/', central_admin.TicketFilterView.as_view(), name='ticket_filter'),
     
     path('registrations/<slug:registration_slug>/schedules/', central_admin.ScheduleListView.as_view(), name='schedule_list'),
     path('registrations/<slug:registration_slug>/schedules/create/', central_admin.ScheduleCreateView.as_view(), name='schedule_create'),
     path('registrations/<slug:registration_slug>/schedules/<slug:schedule_slug>/update/', central_admin.ScheduleUpdateView.as_view(), name='schedule_update'),
     
     path('registrations/<slug:registration_slug>/schedule-groups/', central_admin.ScheduleGroupListView.as_view(), name='schedule_group_list'),
     path('registrations/<slug:registration_slug>/schedule-groups/create/', central_admin.ScheduleGroupCreateView.as_view(), name='schedule_group_create'),
     
     path('registrations/<slug:registration_slug>/bus-records/', central_admin.BusRecordListView.as_view(), name='bus_record_list'),
     path('registrations/<slug:registration_slug>/bus-records/create/', central_admin.BusRecordCreateView.as_view(), name='bus_record_create'),
     path('registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/update/', central_admin.BusRecordUpdateView.as_view(), name='bus_record_update'),
     path('registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/delete/', central_admin.BusRecordDeleteView.as_view(), name='bus_record_delete'),
     
     path('registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/', central_admin.TripListView.as_view(), name='trip_list'),
     path('registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/create/', central_admin.TripCreateView.as_view(), name='trip_create'),
     path('registrations/<slug:registration_slug>/bus-records/<slug:bus_record_slug>/trips/<slug:trip_slug>/delete/', central_admin.TripDeleteView.as_view(), name='trip_delete'),
     
     path('registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/', central_admin.BusSearchFormView.as_view(), name='bus_search'),
     path('registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/available-buses/', central_admin.BusSearchResultsView.as_view(), name='bus_search_results'),
     path('registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/select-bus/<slug:bus_record_slug>/update-ticket/', central_admin.UpdateBusInfoView.as_view(), name='update_bus_info'),
     
     path('registrations/<slug:registration_slug>/bus-requests/', central_admin.BusRequestListView.as_view(), name='bus_request_list'),
     path('registrations/<slug:registration_slug>/bus-requests/open/', central_admin.BusRequestOpenListView.as_view(), name='bus_request_open_list'),
     path('registrations/<slug:registration_slug>/bus-requests/closed/', central_admin.BusRequestClosedListView.as_view(), name='bus_request_closed_list'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/delete/', central_admin.BusRequestDeleteView.as_view(), name='bus_request_delete'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/status/', central_admin.BusRequestStatusUpdateView.as_view(), name='bus_request_status_update'),
     path('registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/comment/', central_admin.BusRequestCommentView.as_view(), name='bus_request_comment'),
     
     path('registrations/student-groups/filter/', central_admin.StudentGroupFilterView.as_view(), name='student_group_filter'),
     
     path('more/', central_admin.MoreMenuView.as_view(), name='more_menu'),
     
     path('exported-file/<slug:slug>/', exported_file_download, name='exported_file_download'),
     
     path('registrations/<slug:registration_slug>/generate-student-pass/', GenerateStudentPassView.as_view(), name='generate_student_pass'),
     
     path('student-pass/download/<slug:slug>/', StudentPassFileDownloadView.as_view(), name='student_pass_file_download'),
     
     path('registrations/<slug:registration_slug>/bus-records/export-pdf/', central_admin.BusRecordExportPDFView.as_view(), name='bus_record_export_pdf'),

     path('reservations/', ReservationListView.as_view(), name='reservation'),

     path('reservations/<slug:slug>/', ReservationDetailView.as_view(), name='reservation_detail'),
     path('reservations/<slug:slug>/approve/', central_admin.ReservationApproveView.as_view(), name='reservation_approve'),
     path('reservations/<slug:slug>/reject/', central_admin.ReservationRejectView.as_view(), name='reservation_reject'),
     path('reservations/<slug:slug>/assign-bus/', central_admin.BusAssignmentCreateView.as_view(), name='bus_assignment_create'),
     path('reservations/bus-assignment/<int:assignment_id>/delete/', central_admin.BusAssignmentDeleteView.as_view(), name='bus_assignment_delete'),
]