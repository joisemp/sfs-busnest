"""
institution_admin.py - URL configuration for institution admin operations in the services app

This module defines URL patterns for institution admin views, including registration management, ticket management,
bus info updates, stop and schedule selection, bus requests, receipts, student groups, bulk updates, and ticket export.

URL Patterns (detailed):
- registrations/: List all registrations for the institution admin.
- registrations/<slug:registration_slug>/tickets/: List all tickets for a registration.
- registrations/<slug:registration_slug>/tickets/<slug:ticket_slug>/: Update a ticket.
- registrations/<slug:registration_slug>/tickets/<slug:ticket_slug>/delete/: Delete a ticket.
- registrations/<slug:registration_code>/update-bus-info/<slug:ticket_id>/search-bus/: Search for available buses for a ticket.
- change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-stop/: Select a stop for changing bus info.
- change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-schedule/: Select a schedule group for changing bus info.
- change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-bus/update-ticket/: Show available buses and update ticket.
- change-bus/registrations/<slug:registration_code>/tickets/<slug:ticket_id>/select-bus/<slug:bus_slug>/update-ticket/: Update ticket with selected bus.
- registrations/<slug:registration_slug>/bus-requests/: List all bus requests for a registration.
- registrations/<slug:registration_slug>/bus-requests/open/: List open bus requests.
- registrations/<slug:registration_slug>/bus-requests/closed/: List closed bus requests.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/delete/: Delete a bus request.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/status/: Update the status of a bus request.
- registrations/<slug:registration_slug>/bus-requests/<slug:bus_request_slug>/comment/: Add a comment to a bus request.
- registrations/<slug:registration_slug>/receipts/: List all receipts for a registration.
- registrations/<slug:registration_slug>/receipts/upload/: Upload receipt data file.
- registrations/<slug:registration_slug>/receipts/add/: Add a new receipt.
- registrations/<slug:registration_slug>/receipts/<slug:receipt_slug>/delete/: Delete a receipt.
- registrations/<slug:registration_slug>/student-groups/: List all student groups for a registration.
- registrations/<slug:registration_slug>/student-groups/create/: Create a new student group.
- registrations/<slug:registration_slug>/student-groups/<slug:student_group_slug>/update/: Update a student group.
- registrations/<slug:registration_slug>/student-groups/<slug:student_group_slug>/delete/: Delete a student group.
- registrations/<slug:registration_slug>/bulk-update-student-group/: Bulk update student groups via file upload.
- registrations/<slug:registration_slug>/bulk-update-student-group/confirm/: Confirm bulk update of student groups.
- export/<slug:registration_slug>/: Export tickets for a registration.
"""

from django.urls import path
from services.views import institution_admin
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from services.models import ExportedFile

app_name = 'institution_admin'


urlpatterns = [
     path('registrations/', institution_admin.RegistrationListView.as_view(), name='registration_list'),
     
     path('reservations/', institution_admin.ReservationListView.as_view(), name='reservation_list'),
     path('reservations/create/', institution_admin.ReservationCreateView.as_view(), name='reservation_create'),
     path('reservations/<slug:slug>/', institution_admin.ReservationDetailView.as_view(), name='reservation_detail'),
     path('reservations/<slug:slug>/delete/', institution_admin.ReservationDeleteView.as_view(), name='reservation_delete'),
     
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
     
     path('registrations/<slug:registration_slug>/bulk-update-student-group/', institution_admin.BulkStudentGroupUpdateView.as_view(), name='bulk_update_student_group'),
     path('registrations/<slug:registration_slug>/bulk-update-student-group/confirm/', institution_admin.BulkStudentGroupUpdateConfirmView.as_view(), name='bulk_update_student_group_confirm'),
     
     path('export/<slug:registration_slug>/', institution_admin.TicketExportView.as_view(), name='ticket_export'),
]