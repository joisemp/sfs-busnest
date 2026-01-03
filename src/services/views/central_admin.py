"""
central_admin.py - Views for central admin operations in the services app

This module contains Django class-based and function-based views for central admin operations, including:
- Dashboard, institution, bus, and people management
- Registration, route, stop, schedule, schedule group, and ticket management
- Bus records, trips, FAQs, and bus requests
- File uploads and exports
- User activity logging and notifications

Each view is documented with its purpose, attributes, and methods. The views leverage Django's generic class-based views and custom mixins for access control and business logic.
"""

import threading
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from core.models import UserProfile
from django.db import transaction, IntegrityError
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.db.models import Q, Count, F, Sum
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib import messages
from urllib.parse import urlencode
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import FileResponse
import io

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin, RegistrationClosedOnlyAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import (
    ListView, 
    CreateView, 
    UpdateView, 
    DeleteView, 
    DetailView, 
    TemplateView, 
    View, 
    FormView
)
from services.models import (
    Institution, 
    Bus, 
    Stop, 
    Route, 
    RouteFile, 
    Registration, 
    StudentGroup, 
    Ticket, 
    FAQ, 
    Schedule, 
    BusRequest, 
    BusRecord, 
    BusFile, 
    Trip, 
    ScheduleGroup, 
    BusRequestComment, 
    UserActivity, 
    Notification,
    StudentPassFile,
    BusReservationRequest,
    BusReservationAssignment,
    TripExpense,
    log_user_activity
)

from services.forms.central_admin import (
    PeopleCreateForm, 
    PeopleUpdateForm, 
    InstitutionForm, 
    BusForm, 
    RouteForm, 
    StopForm, 
    RegistrationForm, 
    FAQForm, 
    ScheduleForm, 
    BusRecordCreateForm, 
    BusRecordUpdateForm, 
    BusSearchForm, 
    TripCreateForm, 
    ScheduleGroupForm, 
    BusRequestStatusForm, 
    BusRequestCommentForm,
    StopTransferForm,
    BusAssignmentForm,
    TripExpenseForm,
    AutoAssignDriversForm
)

from services.tasks import process_uploaded_route_excel, send_email_task, export_tickets_to_excel, process_uploaded_bus_excel, generate_student_pass, export_filtered_tickets_to_excel
from services.utils.transfer_stop import move_stop_and_update_tickets
from datetime import datetime

User = get_user_model()


class DashboardView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    """
    DashboardView is a Django class-based view that renders the central admin dashboard.
    Inherits:
        LoginRequiredMixin: Ensures that the user is authenticated.
        CentralAdminOnlyAccessMixin: Ensures that the user has central admin access.
        TemplateView: Renders a template.
    Attributes:
        template_name (str): The path to the template used to render the view.
    Methods:
        get_context_data(**kwargs):
            Adds additional context data to the template, including:
            - org: The organization associated with the current user's profile.
            - active_registrations: The count of active registrations for the organization.
            - buses_available: The count of buses available for the organization.
            - institution_count: The count of institutions associated with the organization.
            - recent_activities: The 10 most recent user activities for the organization, ordered by timestamp.
    """
    template_name = 'central_admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.user.profile.org
        context['org'] = org
        context['active_registrations'] = Registration.objects.filter(org=org).count()
        context['buses_available'] = Bus.objects.filter(org=org).count()
        context['institution_count'] = Institution.objects.filter(org=org).count()
        context['recent_activities'] = UserActivity.objects.filter(org=org).order_by('-timestamp')[:10]
        
        # Add ticket statistics
        context['total_tickets'] = Ticket.objects.filter(org=org, is_terminated=False).count()
        context['total_stops'] = Stop.objects.filter(org=org).count()
        context['total_routes'] = Route.objects.filter(org=org).count()
        
        return context


class InstitutionListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    InstitutionListView is a Django class-based view that displays a list of institutions.
    It inherits from LoginRequiredMixin, CentralAdminOnlyAccessMixin, and ListView.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (Institution).
        context_object_name (str): The name of the context variable that will contain the list of institutions.
    Methods:
        get_queryset(self):
            Retrieves the queryset of institutions filtered by the organization of the logged-in user.
            If a search term is provided via GET parameters, it filters the queryset further based on the search term.
        get_context_data(self, **kwargs):
            Adds the search term to the context data to be used in the template.
    """
    template_name = 'central_admin/institution_list.html'
    model = Institution
    context_object_name = 'institutions'
    
    def get_queryset(self):
        self.search_term = self.request.GET.get('search', '')
        queryset = Institution.objects.filter(org=self.request.user.profile.org)
        if self.search_term:
            queryset = queryset.filter(
                Q(name__icontains=self.search_term) |
                Q(label__icontains=self.search_term) |
                Q(incharge__first_name__icontains=self.search_term) |
                Q(email__icontains=self.search_term)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.search_term
        return context
    

class InstitutionCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    InstitutionCreateView is a Django class-based view that handles the creation of new Institution instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (Institution).
        form_class (Form): The form class used to create an Institution instance.
    Methods:
        get_form(self, form_class=None):
            Customizes the form to filter the 'incharge' field queryset to include only users who are institution admins
            within the same organization as the current user.
        form_valid(self, form):
            Saves the new Institution instance, assigns the organization based on the current user's profile,
            logs the creation activity, and redirects to the institution list view.
    """
    template_name = 'central_admin/institution_create.html'
    model = Institution
    form_class = InstitutionForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, role=UserProfile.INSTITUTION_ADMIN)
        return form
    
    def form_valid(self, form):
        institution = form.save(commit=False)
        user = self.request.user
        institution.org = user.profile.org
        institution.save()
        log_user_activity(user, f"Created Insitution : {institution.name}", f"{institution.name} with {institution.incharge.first_name} {institution.incharge.last_name} as incharge was created.")
        return redirect('central_admin:institution_list')
    

class InstitutionUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View to handle the update of an Institution.
    Inherits from:
        LoginRequiredMixin: Ensures that the user is logged in.
        CentralAdminOnlyAccessMixin: Ensures that the user has central admin access.
        UpdateView: Generic view to handle update operations.
    Attributes:
        model (Institution): The model to be updated.
        form_class (InstitutionForm): The form class used to update the model.
        template_name (str): The template used to render the update form.
        success_url (str): The URL to redirect to upon successful update.
    Methods:
        get_form(form_class=None):
            Customizes the form to filter the 'incharge' field queryset based on the user's organization and role.
        form_valid(form):
            Handles the form submission. Saves the institution, logs the update action, and handles any integrity errors.
    """
    model = Institution
    form_class = InstitutionForm
    template_name = 'central_admin/institution_update.html'
    success_url = reverse_lazy('central_admin:institution_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, role=UserProfile.INSTITUTION_ADMIN)
        return form

    def form_valid(self, form):
        try:
            institution = form.save()
        except IntegrityError as e:
            form.add_error(None, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
        institution.save()
        user = self.request.user
        action = f"Updated Institution: {institution.name}"
        description = f"{institution.name} with {institution.incharge.first_name} {institution.incharge.last_name} as incharge was updated."
        return super().form_valid(form)


class InstitutionDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View to handle the deletion of an institution.
    """
    model = Institution
    template_name = 'central_admin/institution_confirm_delete.html'
    success_url = reverse_lazy('central_admin:institution_list')

    def delete(self, request, *args, **kwargs):
        institution = self.get_object()
        user = self.request.user
        log_user_activity(user, f"Deleted Institution: {institution.name}", f"{institution.name} was deleted.")
        return super().delete(request, *args, **kwargs)


class BusListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    BusListView is a Django class-based view that displays a list of Bus objects.
    This view inherits from:
    - LoginRequiredMixin: Ensures that the user is authenticated.
    - CentralAdminOnlyAccessMixin: Ensures that the user has central admin access.
    - ListView: Provides the ability to display a list of objects.
    Attributes:
        model (Bus): The model that this view will display.
        template_name (str): The path to the template that will render the view.
        context_object_name (str): The name of the context variable that will contain the list of buses.
    Methods:
        get_queryset(self):
            Returns a queryset of Bus objects filtered by the organization of the currently logged-in user.
    """
    model = Bus
    template_name = 'central_admin/bus_list.html'
    context_object_name = 'buses'
    
    def get_queryset(self):
        queryset = Bus.objects.filter(org=self.request.user.profile.org)
        return queryset


class BusCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    BusCreateView is a Django class-based view that handles the creation of new Bus instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (Bus).
        form_class (Form): The form class used to create a Bus instance.
    Methods:
        form_valid(self, form):
            Saves the new Bus instance, assigns the organization based on the current user's profile,
            logs the creation activity, and redirects to the bus list view.
    """
    template_name = 'central_admin/bus_create.html'
    model = Bus
    form_class = BusForm
    
    def form_valid(self, form):
        bus = form.save(commit=False)
        user = self.request.user
        bus.org = user.profile.org
        bus.save()
        log_user_activity(user, f"Created Bus: {bus.registration_no}", f"Bus {bus.registration_no} was created.")
        return redirect('central_admin:bus_list')
    
    
class BusUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    BusUpdateView is a Django class-based view that handles the update of existing Bus instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (Bus).
        form_class (Form): The form class used to update a Bus instance.
        success_url (str): The URL to redirect to upon successful update.
    Methods:
        form_valid(self, form):
            Handles the form submission, saves the updated Bus instance, logs the update activity,
            and redirects to the bus list view.
    """
    model = Bus
    form_class = BusForm
    template_name = 'central_admin/bus_update.html'
    success_url = reverse_lazy('central_admin:bus_list')

    def form_valid(self, form):
        bus = form.save()
        user = self.request.user
        log_user_activity(user, f"Updated Bus: {bus.registration_no}", f"Bus {bus.registration_no} was updated.")
        return super().form_valid(form)


class BusFileUploadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for handling the upload of bus files by central admin users.
    This view allows central admin users to upload bus files. It ensures that the user is logged in and has the necessary permissions. Upon successful upload, the bus file is processed asynchronously.
    Attributes:
        template_name (str): The path to the template used for rendering the view.
        model (BusFile): The model associated with this view.
        fields (list): The fields of the model to be displayed in the form.
    Methods:
        form_valid(form):
            Handles the form submission. Associates the uploaded file with the user's organization and user profile, saves the file, and triggers asynchronous processing of the uploaded file.
            Args:
                form (Form): The submitted form instance.
            Returns:
                HttpResponse: A redirect to the bus list view upon successful form submission.
    """
    template_name = 'central_admin/bus_file_upload.html'
    model = BusFile
    fields = ['name', 'file']
    
    def form_valid(self, form):
        bus_file = form.save(commit=False)
        user = self.request.user
        bus_file.org = user.profile.org
        bus_file.user = user
        bus_file.save()
        process_uploaded_bus_excel.delay(user.id, bus_file.file.name, bus_file.org.id)
        return redirect(reverse('central_admin:bus_list'))


class BusDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    BusDeleteView is a Django class-based view that handles the deletion of Bus instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (Bus).
        success_url (str): The URL to redirect to upon successful deletion.
    Methods:
        delete(self, request, *args, **kwargs):
            Handles the deletion of the Bus instance, logs the deletion activity, and redirects to the bus list view.
    """
    model = Bus
    template_name = 'central_admin/bus_confirm_delete.html'
    success_url = reverse_lazy('central_admin:bus_list')

    def delete(self, request, *args, **kwargs):
        bus = self.get_object()
        user = self.request.user
        log_user_activity(user, f"Deleted Bus: {bus.registration_no}", f"Bus {bus.registration_no} was deleted.")
        return super().delete(request, *args, **kwargs)
    

class BusRecordListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    BusRecordListView is a Django class-based view that displays a list of BusRecord objects for the central admin.
    Inherits:
        LoginRequiredMixin: Ensures that the user is logged in.
        CentralAdminOnlyAccessMixin: Ensures that only central admin users can access this view.
        ListView: Provides the default behavior for displaying a list of objects.
    Attributes:
        model (BusRecord): The model that this view will display.
        template_name (str): The template used to render the view.
        context_object_name (str): The context variable name for the list of BusRecord objects.
    Methods:
        get_queryset(self):
            Retrieves the queryset of BusRecord objects based on the user's organization and the registration slug.
            If the 'noneRecords' GET parameter is 'True', filters the queryset to include only records with no associated bus.
        get_context_data(self, **kwargs):
            Adds additional context data to the template, including the registration object and flags for blank records and filter reset.
    """
    model = BusRecord
    template_name = 'central_admin/bus_record_list.html'
    context_object_name = 'bus_records'
    
    def get_queryset(self):
        self.noneRecords = self.request.GET.get('noneRecords')
        if self.noneRecords == 'True':
            queryset = BusRecord.objects.filter(
                org=self.request.user.profile.org, 
                bus=None, 
                registration__slug=self.kwargs["registration_slug"]
            ).select_related('assigned_driver__profile').prefetch_related('trips__route').order_by('label').annotate(
                pickup_ticket_count=Count('pickup_tickets', distinct=True),
                drop_ticket_count=Count('drop_tickets', distinct=True),
                trip_count=Count('trips', distinct=True)
            )
        else:
            queryset = BusRecord.objects.filter(
                org=self.request.user.profile.org, 
                registration__slug=self.kwargs["registration_slug"]
            ).select_related('assigned_driver__profile').prefetch_related('trips__route').order_by('label').annotate(
                pickup_ticket_count=Count('pickup_tickets', distinct=True),
                drop_ticket_count=Count('drop_tickets', distinct=True),
                trip_count=Count('trips', distinct=True)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        
        # Calculate total_km and check for fully filled trips for each bus record
        for record in context['bus_records']:
            trips = record.trips.all()
            record.calculated_total_km = sum(trip.route.total_km or 0 for trip in trips)
            
            # Check if any trip is at full capacity (100%)
            record.has_full_trip = False
            if record.bus:  # Only check if bus is assigned
                for trip in trips:
                    if trip.booking_count >= record.bus.capacity:
                        record.has_full_trip = True
                        break
        
        if BusRecord.objects.filter(org=self.request.user.profile.org, bus=None, registration__slug=self.kwargs["registration_slug"]):
            context["blank_records"] = True
        if self.noneRecords:
            context['reset_filter'] = True
        return context
    

class BusRecordCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    BusRecordCreateView is a Django class-based view that handles the creation of new BusRecord instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (BusRecord).
        form_class (Form): The form class used to create a BusRecord instance.
    Methods:
        get_form(self, form_class=None):
            Customizes the form to filter the 'bus' field queryset to include only buses within the same organization as the current user.
        form_valid(self, form):
            Saves the new BusRecord instance, assigns the organization and registration based on the current user's profile,
            logs the creation activity, and redirects to the bus record list view.
    """
    model = BusRecord
    template_name = 'central_admin/bus_record_create.html'
    form_class = BusRecordCreateForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org = self.request.user.profile.org
        form.fields['bus'].queryset = Bus.objects.filter(org=user_org)
        return form
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['org'] = self.request.user.profile.org
        # Pass the registration to the form for validation
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        kwargs['registration'] = registration
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        # Get the registration based on slug
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        bus = form.cleaned_data['bus']
        
        # Check if a BusRecord already exists
        if BusRecord.objects.filter(bus=bus, registration=registration).exists():
            form.add_error(None, "A record with this bus, schedule and registration already exists.")
            return self.form_invalid(form)

        # Save the BusRecord
        bus_record = form.save(commit=False)
        bus_record.org = self.request.user.profile.org
        bus_record.registration = registration
        bus_record.min_required_capacity = bus.capacity
        bus_record.save()

        # Log user activity
        user = self.request.user
        log_user_activity(user, f"Created BusRecord: {bus_record.label}", f"BusRecord {bus_record.label} was created.")

        messages.success(self.request, "Bus Record created successfully!")
        return redirect(self.get_success_url())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context

    def get_success_url(self):
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class BusRecordUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating an existing BusRecord instance for the central admin.
    Ensures that the user is logged in and has central admin access.
    Attributes:
        model (BusRecord): The model to update.
        template_name (str): Template for the update form.
        form_class (BusRecordUpdateForm): The form class for updating a BusRecord.
        slug_field (str): The field used to look up the BusRecord.
        slug_url_kwarg (str): The URL kwarg for the BusRecord slug.
    Methods:
        form_valid(form):
            Updates the BusRecord, ensuring no duplicate records for the same bus and registration.
            If a duplicate exists, it is unassigned from its bus before saving the new assignment.
            Shows a success message and redirects to the bus record list.
        get_context_data(**kwargs):
            Adds the registration object to the context for use in the template.
        get_success_url():
            Returns the URL to redirect to after a successful update.
    """
    model = BusRecord
    form_class = BusRecordUpdateForm
    template_name = 'central_admin/bus_record_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'bus_record_slug'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['org'] = self.request.user.profile.org
        # Pass the registration to the form for validation
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        kwargs['registration'] = registration
        return kwargs
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org = self.request.user.profile.org
        form.fields['bus'].queryset = Bus.objects.filter(org=user_org)
        return form

    @transaction.atomic
    def form_valid(self, form):
        
        # Fetch registration
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        
        # Get the new bus from the form
        new_bus = form.cleaned_data.get('bus')
        
        
        # Check for existing BusRecord with the same bus and registration
        existing_record = BusRecord.objects.filter(bus=new_bus, registration=registration).exclude(pk=self.object.pk).first()
        if existing_record:
            existing_record.bus = None
            existing_record.save()

        # Save the updated record
        bus_record = form.save(commit=False)
        bus_record.bus = new_bus
        bus_record.save()

        # Success message
        messages.success(self.request, "Bus Record updated successfully!")
        return redirect(self.get_success_url())
    
    def get_context_data(self, **kwargs):
        """
        Adds the registration object to the context for use in the template.
        """
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context

    def get_success_url(self):
        """
        Returns the URL to redirect to after a successful update.
        """
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class BusRecordDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    BusRecordDeleteView is a Django class-based view that handles the deletion of BusRecord instances.
    It requires the user to be logged in and have central admin access.
    Attributes:
        template_name (str): The path to the template used to render the view.
        model (Model): The model associated with this view (BusRecord).
        slug_field (str): The field used to look up the BusRecord.
        slug_url_kwarg (str): The URL kwarg for the BusRecord slug.
    Methods:
        delete(self, request, *args, **kwargs):
            Validates that the BusRecord has no associated trips or tickets before deletion.
            Prevents deletion if there are any trips, pickup tickets, or drop tickets associated.
            Logs the deletion activity and redirects to the bus record list view.
        get_context_data(self, **kwargs):
            Adds the registration object and dependency counts to the context for use in the template.
            Includes trip count, pickup ticket count, drop ticket count, and a can_delete flag.
        get_success_url(self):
            Returns the URL to redirect to after a successful deletion.
    """
    model = BusRecord
    template_name = 'central_admin/bus_record_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'bus_record_slug'

    def delete(self, request, *args, **kwargs):
        bus_record = self.get_object()
        user = self.request.user
        
        # Check if there are any trips associated with this bus record
        if bus_record.trips.exists():
            messages.error(request, f"Cannot delete Bus Record '{bus_record.label}' because it has associated trips. Please delete all trips first.")
            return redirect('central_admin:bus_record_list', registration_slug=self.kwargs['registration_slug'])
        
        # Check if there are any tickets using this bus record for pickup
        if bus_record.pickup_tickets.exists():
            pickup_count = bus_record.pickup_tickets.count()
            messages.error(request, f"Cannot delete Bus Record '{bus_record.label}' because it is assigned as pickup bus for {pickup_count} ticket(s). Please reassign or delete these tickets first.")
            return redirect('central_admin:bus_record_list', registration_slug=self.kwargs['registration_slug'])
        
        # Check if there are any tickets using this bus record for drop
        if bus_record.drop_tickets.exists():
            drop_count = bus_record.drop_tickets.count()
            messages.error(request, f"Cannot delete Bus Record '{bus_record.label}' because it is assigned as drop bus for {drop_count} ticket(s). Please reassign or delete these tickets first.")
            return redirect('central_admin:bus_record_list', registration_slug=self.kwargs['registration_slug'])
        
        log_user_activity(user, f"Deleted Bus Record: {bus_record.label}", f"Bus Record {bus_record.label} was deleted.")
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """
        Adds the registration object and dependency information to the context for use in the template.
        Includes counts of related trips and tickets to determine if deletion is allowed.
        """
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        
        # Add information about related objects that would prevent deletion
        bus_record = self.get_object()
        context["trips_count"] = bus_record.trips.count()
        context["pickup_tickets_count"] = bus_record.pickup_tickets.count()
        context["drop_tickets_count"] = bus_record.drop_tickets.count()
        context["can_delete"] = (context["trips_count"] == 0 and 
                                context["pickup_tickets_count"] == 0 and 
                                context["drop_tickets_count"] == 0)
        return context

    def get_success_url(self):
        """
        Returns the URL to redirect to after a successful deletion.
        """
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class DriverManagementView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, FormView):
    """
    View for managing driver assignments to bus records.
    Shows form to select assignment strategy.
    
    Methods:
        get_context_data: Displays summary statistics.
        form_valid: Redirects to confirmation page with selected strategy.
    """
    template_name = 'central_admin/driver_management.html'
    form_class = AutoAssignDriversForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        context['registration'] = registration
        
        # Get all bus records for assignment/reassignment
        bus_records_for_assignment = BusRecord.objects.filter(
            org=self.request.user.profile.org,
            registration=registration
        ).select_related('bus', 'assigned_driver__profile').prefetch_related('trips__route').order_by('label')
        
        # Get all available drivers from the organization
        available_drivers = User.objects.filter(
            profile__org=self.request.user.profile.org,
            profile__role=UserProfile.DRIVER
        ).select_related('profile').order_by('profile__first_name')
        
        # Sort drivers by experience (descending)
        drivers_with_experience = []
        for driver in available_drivers:
            drivers_with_experience.append({
                'driver': driver,
                'experience': driver.profile.years_of_experience or 0
            })
        
        drivers_with_experience.sort(key=lambda x: x['experience'], reverse=True)
        
        context['available_drivers'] = drivers_with_experience
        context['total_bus_records'] = bus_records_for_assignment.count()
        context['available_driver_count'] = len(drivers_with_experience)
        
        return context
    
    def form_valid(self, form):
        strategy = form.cleaned_data['assignment_strategy']
        return redirect('central_admin:driver_assignment_confirm', 
                       registration_slug=self.kwargs['registration_slug'],
                       strategy=strategy)


class DriverAssignmentConfirmView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    """
    View for previewing driver assignments before applying.
    Shows detailed preview of assignments based on selected strategy.
    
    Methods:
        get_context_data: Calculates and displays preview of driver assignments.
    """
    template_name = 'central_admin/driver_assignment_confirm.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        strategy = self.kwargs.get('strategy', 'experienced_to_longest')
        
        context['registration'] = registration
        context['selected_strategy'] = strategy
        
        # Get all bus records for assignment/reassignment
        bus_records_for_assignment = BusRecord.objects.filter(
            org=self.request.user.profile.org,
            registration=registration
        ).select_related('bus', 'assigned_driver__profile').prefetch_related('trips__route').order_by('label')
        
        # Calculate total distance for each bus record
        bus_records_with_distance = []
        for record in bus_records_for_assignment:
            trips = record.trips.all()
            total_km = sum(trip.route.total_km or 0 for trip in trips)
            bus_records_with_distance.append({
                'record': record,
                'total_km': total_km,
                'trip_count': trips.count(),
                'current_driver': record.assigned_driver
            })
        
        # Get all available drivers from the organization
        available_drivers = User.objects.filter(
            profile__org=self.request.user.profile.org,
            profile__role=UserProfile.DRIVER
        ).select_related('profile').order_by('profile__first_name')
        
        # Sort drivers by experience (descending)
        drivers_with_experience = []
        for driver in available_drivers:
            drivers_with_experience.append({
                'driver': driver,
                'experience': driver.profile.years_of_experience or 0
            })
        
        drivers_with_experience.sort(key=lambda x: x['experience'], reverse=True)
        
        # Generate preview assignments
        preview_assignments = self._generate_preview_assignments(
            bus_records_with_distance,
            drivers_with_experience,
            strategy
        )
        
        context['preview_assignments'] = preview_assignments
        context['total_bus_records'] = len(bus_records_with_distance)
        context['available_driver_count'] = len(drivers_with_experience)
        
        return context
    
    def _generate_preview_assignments(self, bus_records_with_distance, drivers_with_experience, strategy):
        """
        Generate preview of driver assignments based on strategy.
        Uses round-robin distribution and prioritizes based on experience and distance.
        
        Args:
            bus_records_with_distance: List of bus records with their total distance
            drivers_with_experience: List of drivers with their experience
            strategy: Assignment strategy ('experienced_to_longest' or 'experienced_to_shortest')
        
        Returns:
            List of assignment dictionaries with bus_record, driver, and assignment details
        """
        assignments = []
        
        if not drivers_with_experience:
            return assignments
        
        # Sort bus records by distance based on strategy
        if strategy == 'experienced_to_longest':
            # Sort routes by distance descending (longest first)
            sorted_records = sorted(bus_records_with_distance, key=lambda x: x['total_km'], reverse=True)
        else:  # experienced_to_shortest
            # Sort routes by distance ascending (shortest first)
            sorted_records = sorted(bus_records_with_distance, key=lambda x: x['total_km'])
        
        # Round-robin assignment - each driver assigned only once
        driver_index = 0
        for record_data in sorted_records:
            if driver_index < len(drivers_with_experience):
                assignments.append({
                    'bus_record': record_data['record'],
                    'driver': drivers_with_experience[driver_index]['driver'],
                    'total_km': record_data['total_km'],
                    'trip_count': record_data['trip_count'],
                    'driver_experience': drivers_with_experience[driver_index]['experience'],
                    'current_driver': record_data.get('current_driver')
                })
                driver_index += 1
            else:
                # Not enough drivers - keep current assignment or leave unassigned
                assignments.append({
                    'bus_record': record_data['record'],
                    'driver': None,
                    'total_km': record_data['total_km'],
                    'trip_count': record_data['trip_count'],
                    'driver_experience': None,
                    'current_driver': record_data.get('current_driver')
                })
        
        return assignments


class DriverManagementApplyView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View for applying driver assignments to bus records.
    Validates and applies the assignments based on the selected strategy.
    
    Methods:
        post: Applies driver assignments and logs activity.
    """
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        registration = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        strategy = request.POST.get('assignment_strategy', 'experienced_to_longest')
        
        # Get all bus records for assignment/reassignment
        bus_records_for_assignment = BusRecord.objects.filter(
            org=request.user.profile.org,
            registration=registration
        ).select_related('bus', 'assigned_driver__profile').prefetch_related('trips__route').order_by('label')
        
        # Calculate total distance for each bus record
        bus_records_with_distance = []
        for record in bus_records_for_assignment:
            trips = record.trips.all()
            total_km = sum(trip.route.total_km or 0 for trip in trips)
            bus_records_with_distance.append({
                'record': record,
                'total_km': total_km
            })
        
        # Get all available drivers from the organization
        available_drivers = User.objects.filter(
            profile__org=request.user.profile.org,
            profile__role=UserProfile.DRIVER
        ).select_related('profile').order_by('profile__first_name')
        
        # Sort drivers by experience (descending)
        drivers_with_experience = list(available_drivers)
        drivers_with_experience.sort(
            key=lambda x: x.profile.years_of_experience or 0,
            reverse=True
        )
        
        if not drivers_with_experience:
            messages.warning(request, "No available drivers found for assignment.")
            return redirect('central_admin:bus_record_list', registration_slug=registration.slug)
        
        # Sort bus records by distance based on strategy
        if strategy == 'experienced_to_longest':
            sorted_records = sorted(bus_records_with_distance, key=lambda x: x['total_km'], reverse=True)
        else:  # experienced_to_shortest
            sorted_records = sorted(bus_records_with_distance, key=lambda x: x['total_km'])
        
        # Apply assignment - each driver assigned only once
        assigned_count = 0
        driver_index = 0
        
        for record_data in sorted_records:
            if driver_index < len(drivers_with_experience):
                bus_record = record_data['record']
                driver = drivers_with_experience[driver_index]
                
                # Store old driver info for logging
                old_driver = bus_record.assigned_driver
                
                # Check if this driver is already assigned to another bus record in this registration
                # If yes, clear that assignment first
                existing_assignment = BusRecord.objects.filter(
                    registration=registration,
                    assigned_driver=driver
                ).exclude(pk=bus_record.pk).first()
                
                if existing_assignment:
                    # Clear the previous assignment
                    existing_assignment.assigned_driver = None
                    existing_assignment.save(update_fields=['assigned_driver'])
                    log_user_activity(
                        request.user,
                        f"Cleared driver assignment",
                        f"Driver {driver.profile.first_name} {driver.profile.last_name} " +
                        f"removed from bus record {existing_assignment.label} (reassignment)"
                    )
                
                # Assign driver to new bus record
                bus_record.assigned_driver = driver
                bus_record.save(update_fields=['assigned_driver'])
                
                # Log activity
                action = "reassigned" if old_driver else "assigned"
                log_user_activity(
                    request.user,
                    f"Auto-{action} driver to bus record",
                    f"Driver {driver.profile.first_name} {driver.profile.last_name} " +
                    f"auto-{action} to bus record {bus_record.label} in registration {registration.name}"
                )
                
                assigned_count += 1
                driver_index += 1
        
        unassigned_count = len(sorted_records) - assigned_count
        
        if assigned_count > 0:
            messages.success(
                request,
                f"Successfully assigned/reassigned {assigned_count} driver(s) to bus records."
            )
        
        if unassigned_count > 0:
            messages.warning(
                request,
                f"{unassigned_count} bus record(s) could not be assigned due to insufficient available drivers."
            )
        
        return redirect('central_admin:bus_record_list', registration_slug=registration.slug)


class TripListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for displaying a list of Trip objects associated with a specific BusRecord for central admin users.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (Trip): The Trip model to be listed.
        template_name (str): Template used for rendering the trip list.
        context_object_name (str): The context variable name for the list of trips.
    Methods:
        get_queryset(self):
            Retrieves the queryset of Trip objects filtered by the BusRecord identified by 'bus_record_slug' in the URL kwargs.
        get_context_data(self, **kwargs):
            Extends context data with:
                - 'registration': The Registration object identified by 'registration_slug' in the URL kwargs.
                - 'bus_record': The BusRecord object identified by 'bus_record_slug' in the URL kwargs.
    """
    model = Trip
    template_name = 'central_admin/trip_list.html'
    context_object_name = 'trips'
    
    def get_queryset(self):
        bus_record = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        queryset = Trip.objects.filter(record=bus_record).select_related('route', 'schedule')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["bus_record"] = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        
        # Calculate total km for all trips in this bus record
        trips = context['trips']
        total_km = sum(trip.route.total_km or 0 for trip in trips)
        context['total_km'] = total_km
        
        return context
    

class TripCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new Trip instance in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the standard Django create view functionality.
    Attributes:
        model (Trip): The Trip model to be created.
        template_name (str): Template used for rendering the trip creation form.
        form_class (TripCreateForm): The form class used for trip creation.
    Methods:
        get_form(self, form_class=None):
            Customizes the form's queryset for 'schedule' and 'route' fields based on the registration slug in the URL.
        form_valid(self, form):
            Handles the creation of a Trip instance within an atomic transaction.
            Associates the trip with the correct Registration and BusRecord.
            Handles IntegrityError if a trip with the same schedule already exists.
        get_context_data(self, **kwargs):
            Adds the current Registration object to the template context for use in rendering.
    """
    model = Trip
    template_name = 'central_admin/trip_create.html'
    form_class = TripCreateForm
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        form.fields['schedule'].queryset = Schedule.objects.filter(registration=registration)
        form.fields['route'].queryset = Route.objects.filter(registration=registration)
        return form
    
    @transaction.atomic
    def form_valid(self, form):
        try:
            trip = form.save(commit=False)
            registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
            bus_record = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
            trip.registration = registration
            trip.record = bus_record
            trip.save()
            return HttpResponseRedirect(reverse('central_admin:trip_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'bus_record_slug':self.kwargs['bus_record_slug']}))
        except IntegrityError:
            form.add_error(None, "A trip with the same schedule already exists.")
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    

class TripDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting a Trip instance in the Central Admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DeleteView: Provides the delete functionality for a model instance.
    Attributes:
        model (Trip): The model to be deleted.
        template_name (str): The template used to confirm deletion.
        slug_field (str): The model field used for lookup.
        slug_url_kwarg (str): The URL keyword argument for the slug.
    Methods:
        get_context_data(self, **kwargs):
            Adds 'registration' and 'bus_record' objects to the context based on URL parameters.
            Also checks for related tickets and adds dependency information.
        delete(self, request, *args, **kwargs):
            Checks for tickets associated with this trip before allowing deletion.
        get_success_url(self):
            Returns the URL to redirect to after successful deletion, using 'registration_slug' and 'bus_record_slug' from the URL.
    """
    model = Trip
    template_name = 'central_admin/trip_confirm_delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'trip_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context['bus_record'] = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        
        # Check for tickets associated with this trip
        trip = self.get_object()
        
        # Find tickets that use this trip's schedule and bus record for pickup
        pickup_tickets = Ticket.objects.filter(
            pickup_schedule=trip.schedule,
            pickup_bus_record=trip.record,
            is_terminated=False
        )
        
        # Find tickets that use this trip's schedule and bus record for drop
        drop_tickets = Ticket.objects.filter(
            drop_schedule=trip.schedule,
            drop_bus_record=trip.record,
            is_terminated=False
        )
        
        # Get unique tickets (a ticket might appear in both pickup and drop)
        all_tickets = pickup_tickets.union(drop_tickets)
        ticket_count = all_tickets.count()
        
        context['ticket_count'] = ticket_count
        context['can_delete'] = ticket_count == 0
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """
        Check for tickets associated with this trip before allowing deletion.
        """
        trip = self.get_object()
        
        # Check for tickets that use this trip's schedule and bus record
        pickup_tickets = Ticket.objects.filter(
            pickup_schedule=trip.schedule,
            pickup_bus_record=trip.record,
            is_terminated=False
        )
        
        drop_tickets = Ticket.objects.filter(
            drop_schedule=trip.schedule,
            drop_bus_record=trip.record,
            is_terminated=False
        )
        
        all_tickets = pickup_tickets.union(drop_tickets)
        
        if all_tickets.exists():
            messages.error(
                request,
                f"Cannot delete this trip because it has {all_tickets.count()} ticket(s) associated with it. "
                "Please remove or reassign all tickets before deleting the trip."
            )
            return redirect(self.get_success_url())
        
        messages.success(request, f"Trip '{trip.schedule.name}' for '{trip.record.label}' has been successfully deleted.")
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('central_admin:trip_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'bus_record_slug': self.kwargs['bus_record_slug']})

    
class PeopleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for listing user profiles within the same organization as the currently logged-in user.
    Inherits:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (UserProfile): The model representing user profiles.
        template_name (str): The template used to render the list.
        context_object_name (str): The context variable name for the list of people.
    Methods:
        get_queryset(): Returns a queryset of UserProfile objects filtered by the organization of the current user.
    """
    model = UserProfile
    template_name = 'central_admin/people_list.html'
    context_object_name = 'people'
    
    def get_queryset(self):
        queryset = UserProfile.objects.filter(org=self.request.user.profile.org)
        return queryset
    

class PeopleCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new user profile within the central admin interface.
    Inherits:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides object creation functionality.
    Attributes:
        model (UserProfile): The model associated with this view.
        template_name (str): The template used for rendering the view.
        form_class (PeopleCreateForm): The form used for user profile creation.
        success_url (str): URL to redirect to upon successful creation.
    Methods:
        form_valid(form):
            Handles the creation of a new user and associated user profile.
            - Generates a random password for the new user.
            - Creates a User instance and associates it with the UserProfile.
            - Sets the organization of the new profile to match the current user's organization.
            - Generates a password reset link for the new user.
            - Sends a welcome email with the password reset link.
            - Redirects to the success URL upon success.
            - Handles exceptions and returns form_invalid on error.
    """
    model = UserProfile
    template_name = 'central_admin/people_create.html'
    form_class = PeopleCreateForm
    success_url = reverse_lazy('central_admin:people_list')

    @transaction.atomic
    def form_valid(self, form):
        try:
            userprofile = form.save(commit=False)

            random_password = BaseUserManager().make_random_password()

            user = User.objects.create_user(
                email=form.cleaned_data.get('email'),
                first_name=userprofile.first_name,
                last_name=userprofile.last_name,
                password=random_password,
            )

            userprofile.user = user
            userprofile.org = self.request.user.profile.org
            userprofile.save()
            
            # Generate password reset link
            token_generator = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)

            reset_link = self.request.build_absolute_uri(
                reverse('core:confirm_password_reset', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Only send email if the user is not a driver
            if not userprofile.is_driver:
                subject = "Welcome to SFS Busnest"
                message = (
                f"Hello,\n\n"
                f"Welcome to our BusNest! You have been added to the system by "
                f"{self.request.user.profile.first_name} {self.request.user.profile.last_name}. "
                f"Please set your password using the link below.\n\n"
                f"{reset_link}\n\n"
                f"Best regards,\nSFSBusNest Team"
                )
                recipient_list = [f"{user.email}"]
                
                send_email_task.delay(subject, message, recipient_list)
            
            return redirect(self.success_url)
        except Exception as e:
            print(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
        
        
class PeopleUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating a user's profile in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        UpdateView: Provides update functionality for a single object.
    Attributes:
        model (UserProfile): The model to update.
        form_class (PeopleUpdateForm): The form used for updating the user profile.
        template_name (str): The template used to render the update form.
        success_url (str): The URL to redirect to upon successful update.
    Methods:
        form_valid(form): Handles valid form submissions by calling the parent implementation.
    """
    model = UserProfile
    form_class = PeopleUpdateForm
    template_name = 'central_admin/people_update.html'
    success_url = reverse_lazy('central_admin:people_list')

    def form_valid(self, form):
        return super().form_valid(form)
    

class PeopleDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting a UserProfile instance in the central admin interface.

    Inherits from:
        - LoginRequiredMixin: Ensures the user is authenticated.
        - CentralAdminOnlyAccessMixin: Restricts access to central admin users only.
        - DeleteView: Provides the ability to delete a model instance.

    Attributes:
        model (UserProfile): The model to be deleted.
        template_name (str): The template used to confirm deletion.
        success_url (str): The URL to redirect to upon successful deletion.

    Template:
        central_admin/people_confirm_delete.html

    Redirects:
        On successful deletion, redirects to the people list page in the central admin section.
    """
    model = UserProfile
    template_name = 'central_admin/people_confirm_delete.html'
    success_url = reverse_lazy('central_admin:people_list')


class RouteListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for displaying a paginated list of Route objects for a specific registration in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (Route): The model to list.
        template_name (str): Template used for rendering the list.
        context_object_name (str): Name of the context variable for the list of routes.
        paginate_by (int): Number of routes per page.
    Methods:
        get_queryset(self):
            Returns a queryset of Route objects filtered by the organization of the currently logged-in user.
            Supports optional search by route name via the 'search' GET parameter.
        get_context_data(self, **kwargs):
            Adds the current registration and search term to the context for template rendering.
    """
    model = Route
    template_name = 'central_admin/route_list.html'
    context_object_name = 'routes'
    paginate_by = 10  # Add pagination with 10 items per page

    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        self.search_term = self.request.GET.get('search', '')
        queryset = Route.objects.filter(org=self.request.user.profile.org, registration=registration).annotate(
            stop_count=Count('stops', distinct=True),
            pickup_ticket_count=Count('stops__ticket_pickups', distinct=True),
            drop_ticket_count=Count('stops__ticket_drops', distinct=True)
        )
        if self.search_term:
            queryset = queryset.filter(name__icontains=self.search_term)
        
        # Natural sorting - convert to list and sort with natural key
        routes_list = list(queryset)
        routes_list.sort(key=lambda x: self._natural_sort_key(x.name))
        return routes_list
    
    def _natural_sort_key(self, text):
        """
        Generate a key for natural sorting that handles numbers correctly.
        Converts 'Route 10' to come after 'Route 9' instead of after 'Route 1'.
        """
        import re
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs['registration_slug'])
        context["search_term"] = self.search_term
        
        # Preserve query parameters for pagination
        query_dict = self.request.GET.copy()
        if 'page' in query_dict:
            query_dict.pop('page')
        context['query_params'] = query_dict.urlencode()
        
        return context
    

class RouteFileUploadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for handling the upload of route files by central admin users.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides functionality for creating new RouteFile instances.
    Attributes:
        template_name (str): Path to the template used for rendering the upload form.
        model (Model): The RouteFile model associated with this view.
        fields (list): List of fields to include in the form ('name', 'file').
    Methods:
        form_valid(form):
            Handles the logic after a valid form submission:
                - Associates the uploaded file with the user's organization.
                - Saves the RouteFile instance.
                - Retrieves the related Registration object using the 'registration_slug' URL parameter.
                - Triggers an asynchronous task to process the uploaded Excel file.
                - Redirects to the route list view for the given registration.
    """
    template_name = 'central_admin/route_file_upload.html'
    model = RouteFile
    fields = ['name', 'file']
    
    def form_valid(self, form):
        route_file = form.save(commit=False)
        user = self.request.user
        route_file.org = user.profile.org
        route_file.save()
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        process_uploaded_route_excel.delay(self.request.user.id, route_file.file.name, user.profile.org.id, registration.id)
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))
        

class RouteCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new Route instance within the Central Admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the standard Django create view functionality.
    Attributes:
        template_name (str): Path to the template used for rendering the view.
        model (Model): The Route model associated with this view.
        form_class (Form): The form class used to create a Route.
    Methods:
        get_context_data(self, **kwargs):
            Adds the related Registration object to the template context based on the 'registration_slug' URL parameter.
        form_valid(self, form):
            Associates the new Route with the current user's organization and the specified Registration.
            Saves the Route and redirects to the route list view for the current registration.
    """
    template_name = 'central_admin/route_create.html'
    model = Route
    form_class = RouteForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context['registration']=registration
        return context
    
    def form_valid(self, form):
        route = form.save(commit=False)
        user = self.request.user
        route.org = user.profile.org
        route.registration=Registration.objects.get(slug=self.kwargs["registration_slug"])
        route.save()
        return redirect(reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']}))
    
    
class RouteUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating a Route instance within the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        UpdateView: Provides update functionality for a model instance.
    Attributes:
        model (Route): The model to update.
        form_class (RouteForm): The form used for updating the Route.
        template_name (str): The template used to render the update form.
        slug_field (str): The model field used for lookup via slug.
        slug_url_kwarg (str): The URL keyword argument for the route's slug.
    Methods:
        get_context_data(self, **kwargs):
            Adds the related Registration object to the context using the 'registration_slug' from the URL.
        get_success_url(self):
            Returns the URL to redirect to after a successful update, specifically the route list for the given registration.
    """
    model = Route
    form_class = RouteForm
    template_name = 'central_admin/route_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'route_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    
    
class RouteDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting a Route instance within the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DeleteView: Provides the delete object functionality.
    Attributes:
        model (Route): The model to be deleted.
        template_name (str): Template used to confirm deletion.
        slug_field (str): The field used for lookup.
        slug_url_kwarg (str): The URL keyword argument for the Route slug.
    Methods:
        get_context_data(self, **kwargs):
            Adds the related Registration object to the context using the 'registration_slug' from the URL.
        get_success_url(self):
            Returns the URL to redirect to after successful deletion, specifically the route list for the given registration.
    """
    model = Route
    template_name = 'central_admin/route_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'route_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:route_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class StopListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for displaying a list of Stop objects filtered by a specific Route and Registration.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Generic Django view for displaying a list of objects.
    Attributes:
        model (Stop): The model associated with this view.
        template_name (str): The template used to render the stop list.
        context_object_name (str): The context variable name for the list of stops.
    Methods:
        get_queryset(self):
            Returns a queryset of Stop objects filtered by the route and registration
            specified in the URL parameters ('route_slug' and 'registration_slug').
        get_context_data(self, **kwargs):
            Adds the current Route and Registration objects to the context, based on
            the URL parameters.
    """
    model = Stop
    template_name = 'central_admin/stop_list.html'
    context_object_name = 'stops'
    
    def get_queryset(self):
        route = Route.objects.get(slug=self.kwargs['route_slug'])
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        queryset = Stop.objects.filter(registration=registration, route=route).annotate(
            pickup_ticket_count=Count('ticket_pickups', distinct=True),
            drop_ticket_count=Count('ticket_drops', distinct=True)
        )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = Route.objects.get(slug=self.kwargs['route_slug'])
        context["registration"] = Registration.objects.get(slug=self.kwargs['registration_slug'])
        return context
    

class StopCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new Stop instance within the Central Admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides object creation functionality.
    Attributes:
        template_name (str): Path to the template used for rendering the view.
        model (Model): The Stop model associated with this view.
        form_class (Form): The form class used for Stop creation.
    Methods:
        get_context_data(self, **kwargs):
            Adds the Registration object (based on 'registration_slug' from URL kwargs) to the context.
        form_valid(self, form):
            Handles the logic for saving a new Stop instance, associating it with the current user's organization,
            the specified Registration, and Route (all determined by URL kwargs). Redirects to the stop list view
            upon successful creation.
    """
    template_name = 'central_admin/stop_create.html'
    model = Stop
    form_class = StopForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def form_valid(self, form):
        stop = form.save(commit=False)
        route = Route.objects.get(slug=self.kwargs['route_slug'])
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        user = self.request.user
        stop.org = user.profile.org
        stop.registration = registration
        stop.route = route
        stop.save()
        return HttpResponseRedirect(reverse('central_admin:stop_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'route_slug': self.kwargs['route_slug']}))
    

class StopUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating a Stop instance in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        UpdateView: Provides update functionality for a model instance.
    Attributes:
        model (Stop): The model associated with this view.
        form_class (StopForm): The form used for updating the Stop instance.
        template_name (str): The template used to render the update form.
        slug_field (str): The model field used for slug lookup.
        slug_url_kwarg (str): The URL keyword argument for the stop slug.
    Methods:
        get_context_data(self, **kwargs): Adds the related Registration object to the context using the 'registration_slug' from the URL.
        get_success_url(self):
            Returns the URL to redirect to after a successful update, using 'registration_slug' and 'route_slug' from the URL kwargs.
    """
    model = Stop
    form_class = StopForm
    template_name = 'central_admin/stop_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'stop_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:stop_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'route_slug': self.kwargs['route_slug']})
    

class StopDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting a Stop instance within the Central Admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DeleteView: Provides the delete object functionality.
    Attributes:
        model (Stop): The model to be deleted.
        template_name (str): Template used to confirm deletion.
        slug_field (str): The field used to identify the Stop instance.
        slug_url_kwarg (str): The URL keyword argument for the Stop slug.
    Methods:
        get_context_data(self, **kwargs):
            Adds the related Registration object to the context using the 'registration_slug' from the URL.
        get_success_url(self):
            Returns the URL to redirect to after successful deletion, using 'registration_slug' and 'route_slug' from the URL kwargs.
    """
    model = Stop
    template_name = 'central_admin/stop_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'stop_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:stop_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'route_slug': self.kwargs['route_slug']})


class RegistraionListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for listing Registration objects associated with the current user's organization.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (Registration): The model to list.
        template_name (str): Template used for rendering the registration list.
        context_object_name (str): Context variable name for the registrations list.
    Methods:
        get_queryset(self):
            Returns a queryset of Registration objects filtered by the organization
            of the currently logged-in user's profile.
    """
    model = Registration
    template_name = 'central_admin/registration_list.html'
    context_object_name = 'registrations'
    
    def get_queryset(self):
        queryset = Registration.objects.filter(org=self.request.user.profile.org)
        return queryset
    
    
class RegistrationCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new Registration instance in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the logic for creating model instances.
    Attributes:
        template_name (str): Path to the template used for rendering the registration creation form.
        model (Model): The Registration model to be created.
        form_class (Form): The form class used for registration creation.
    Methods:
        form_valid(form):
            Handles valid form submissions. Associates the new Registration with the current user's organization,
            saves the instance, and redirects to the registration list view.
    """
    template_name = 'central_admin/registration_create.html'
    model = Registration
    form_class = RegistrationForm
    
    def form_valid(self, form):
        registration = form.save(commit=False)
        user = self.request.user
        registration.org = user.profile.org
        registration.save()
        form.save_m2m()
        return redirect('central_admin:registration_list')
    
    
class RegistrationDetailView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DetailView):
    """
    View for displaying the details of a Registration instance for central admin users.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DetailView: Provides detail view functionality for a single object.
    Attributes:
        template_name (str): Path to the template used for rendering the view.
        model (Model): The Django model associated with this view (Registration).
        context_object_name (str): The context variable name for the Registration object.
        slug_field (str): The model field used for slug lookup.
        slug_url_kwarg (str): The URL keyword argument for the slug.
    Methods:
        get_context_data(self, **kwargs):
            Extends the context data with the 10 most recent tickets related to the registration,
            filtered by the current user's organization.
    """
    template_name = 'central_admin/registration_detail.html'
    model = Registration
    context_object_name = 'registration'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tickets = self.object.tickets.filter(org=self.request.user.profile.org).order_by('-created_at')[:10]
        context['recent_tickets'] = tickets
        return context


class RegistrationUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating a Registration instance in the central admin interface.
    Inherits from:
        - LoginRequiredMixin: Ensures the user is authenticated.
        - CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        - UpdateView: Provides update functionality for a model instance.
    Attributes:
        model (Registration): The model to update.
        form_class (RegistrationForm): The form used to update the model.
        template_name (str): The template used to render the update form.
        slug_field (str): The model field used for lookup via slug.
        slug_url_kwarg (str): The URL keyword argument for the slug.
    Methods:
        form_valid(form):
            Called when a valid form is submitted. Proceeds with the default update behavior.
        get_context_data(**kwargs):
            Adds additional context to the template, including:
                - 'faq_form': The FAQForm class.
                - 'protocol': The request scheme (http/https).
                - 'domain': The current host/domain.
        get_success_url():
            Returns the URL to redirect to after a successful update, pointing to the registration detail view.
    """
    model = Registration
    form_class = RegistrationForm
    template_name = 'central_admin/registration_update.html'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'

    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_form'] = FAQForm
        context['protocol'] = self.request.scheme
        context['domain'] = self.request.get_host()
        return context
    
    def get_success_url(self):
        return reverse('central_admin:registration_detail', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class RegistrationDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting a Registration instance in the central admin interface.

    Inherits from:
        - LoginRequiredMixin: Ensures the user is authenticated.
        - CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        - DeleteView: Provides the ability to delete a model instance.

    Attributes:
        model (Registration): The model to be deleted.
        template_name (str): Template used to confirm deletion.
        slug_field (str): The field used to identify the object in the URL.
        slug_url_kwarg (str): The URL keyword argument for the slug.
        success_url (str): URL to redirect to after successful deletion.

    Template:
        central_admin/registration_confirm_delete.html

    URL pattern should include 'registration_slug' as a keyword argument.
    """
    model = Registration
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'
    success_url = reverse_lazy('central_admin:registration_list')
    
    
class TicketListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    Displays a paginated list of Ticket objects for a specific Registration, restricted to central admin users.

    Features:
        - Supports filtering by institution, pickup/drop points, schedule, buses, student group, pickup/drop schedule, and a general search term.
        - Filtered status and filter options are provided in the context for use in the template.
        - Results are ordered by creation date (most recent first).

    Attributes:
        model (Ticket): The model associated with this view.
        template_name (str): The template used to render the ticket list.
        context_object_name (str): The context variable name for the ticket queryset.
        paginate_by (int): Number of tickets to display per page.

    Methods:
        get_queryset(self):
            Returns a queryset of Ticket objects filtered by registration and GET parameters.
            Sets a flag indicating if any filters are applied.
        get_context_data(self, **kwargs):
            Extends the context with filter status, filter options (pickup/drop points, schedules, institutions, bus records, student groups), the current registration, search term, and selected pickup/drop schedules.
    """
    model = Ticket
    template_name = 'central_admin/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 15
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        queryset = Ticket.objects.filter(
            org=self.request.user.profile.org, 
            registration=self.registration,
            is_terminated=False
        ).order_by('-created_at')
        institution = self.request.GET.get('institution')
        pickup_points = self.request.GET.getlist('pickup_point')
        drop_points = self.request.GET.getlist('drop_point')
        schedule = self.request.GET.get('schedule')
        pickup_buses = self.request.GET.getlist('pickup_bus')
        drop_buses = self.request.GET.getlist('drop_bus')
        student_group = self.request.GET.get('student_group')
        pickup_schedule = self.request.GET.get('pickup_schedule')
        drop_schedule = self.request.GET.get('drop_schedule')
        filters = False
        self.search_term = self.request.GET.get('search', '')
        if self.search_term:
            queryset = Ticket.objects.filter(
                Q(student_name__icontains=self.search_term) |
                Q(student_email__icontains=self.search_term) |
                Q(student_id__icontains=self.search_term) |
                Q(contact_no__icontains=self.search_term) |
                Q(alternative_contact_no__icontains=self.search_term),
                org=self.request.user.profile.org,
                registration=self.registration,
                is_terminated=False
            )

        # Apply filters based on GET parameters and update the filters flag
        if institution:
            queryset = queryset.filter(institution_id=institution)
            filters = True
        if pickup_points and not pickup_points == ['']:
            queryset = queryset.filter(pickup_point_id__in=pickup_points)
            filters = True
        if drop_points and not drop_points == ['']:
            queryset = queryset.filter(drop_point_id__in=drop_points)
            filters = True
        if schedule:
            queryset = queryset.filter(schedule_id=schedule)
            filters = True
        if pickup_buses and not pickup_buses == ['']:
            queryset = queryset.filter(pickup_bus_record_id__in=pickup_buses)
            filters = True
        if drop_buses and not drop_buses == ['']:
            queryset = queryset.filter(drop_bus_record_id__in=drop_buses)
            filters = True
        if student_group:
            queryset = queryset.filter(student_group_id=student_group)
            filters = True
        if pickup_schedule:
            queryset = queryset.filter(pickup_schedule_id=pickup_schedule)
            filters = True
        if drop_schedule:
            queryset = queryset.filter(drop_schedule_id=drop_schedule)
            filters = True
        self.filters = filters
        self.selected_pickup_schedule = pickup_schedule
        self.selected_drop_schedule = drop_schedule
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = self.filters
        context['registration'] = self.registration
        context['pickup_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration).order_by('name')
        context['drop_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration).order_by('name')
        context['schedules'] = Schedule.objects.filter(org=self.registration.org, registration=self.registration)
        context['institutions'] = Institution.objects.filter(org=self.registration.org)
        context['bus_records'] = BusRecord.objects.filter(org=self.registration.org, registration=self.registration).order_by("label")
        context['student_groups'] = StudentGroup.objects.filter(org=self.request.user.profile.org).order_by('name')
        context['search_term'] = self.search_term
        context['selected_pickup_schedule'] = self.selected_pickup_schedule
        context['selected_drop_schedule'] = self.selected_drop_schedule
        
        # Preserve query parameters for pagination
        query_dict = self.request.GET.copy()
        if 'page' in query_dict:
            query_dict.pop('page')
        context['query_params'] = query_dict.urlencode()
        
        return context
    

class TicketFilterView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    TicketFilterView displays a paginated list of Ticket objects filtered by various criteria for central admin users.
    Inherits:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (Ticket): The model to list.
        template_name (str): The template used for rendering the view.
        context_object_name (str): The context variable name for the tickets.
        paginate_by (int): Number of tickets per page.
    Methods:
        get_queryset(self):
            Returns a queryset of Ticket objects filtered by:
                - Registration (from URL kwargs)
                - Organization (from user's profile)
                - Optional GET parameters:
                    - start_date: Filters tickets created on or after this date.
                    - end_date: Filters tickets created on or before this date.
                    - institution: Filters by institution slug.
                    - ticket_type: Filters by ticket type.
                    - student_group: Filters by student group ID.
        get_context_data(self, **kwargs):
            Adds additional context to the template, including:
                - registration: The current Registration object.
                - start_date, end_date: The selected date filters.
                - institutions: List of institutions for the user's organization.
                - selected_institution: The selected institution slug.
                - ticket_types: Available ticket types.
                - selected_ticket_type: The selected ticket type.
    """
    model = Ticket
    template_name = 'central_admin/ticket_filter.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)

        queryset = Ticket.objects.filter(
            org=self.request.user.profile.org, 
            registration=self.registration,
            is_terminated=False
        )

        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        institution_slug = self.request.GET.get('institution')  # Changed to slug
        ticket_type = self.request.GET.get('ticket_type')
        student_group_id = self.request.GET.get('student_group')
        pickup_bus = self.request.GET.get('pickup_bus')
        drop_bus = self.request.GET.get('drop_bus')
        pickup_schedule = self.request.GET.get('pickup_schedule')
        drop_schedule = self.request.GET.get('drop_schedule')
        pickup_stop = self.request.GET.get('pickup_stop')
        drop_stop = self.request.GET.get('drop_stop')

        if start_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(end_date))
        if institution_slug:
            queryset = queryset.filter(institution__slug=institution_slug)  # Filter by slug
        if ticket_type:
            queryset = queryset.filter(ticket_type=ticket_type)
        if student_group_id:
            queryset = queryset.filter(student_group_id=student_group_id)
        if pickup_bus:
            queryset = queryset.filter(pickup_bus_record_id=pickup_bus)
        if drop_bus:
            queryset = queryset.filter(drop_bus_record_id=drop_bus)
        if pickup_schedule:
            queryset = queryset.filter(pickup_schedule_id=pickup_schedule)
        if drop_schedule:
            queryset = queryset.filter(drop_schedule_id=drop_schedule)
        if pickup_stop:
            queryset = queryset.filter(pickup_point_id=pickup_stop)
        if drop_stop:
            queryset = queryset.filter(drop_point_id=drop_stop)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.registration
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['institutions'] = Institution.objects.filter(org=self.request.user.profile.org)
        context['selected_institution'] = self.request.GET.get('institution', '')
        context['ticket_types'] = Ticket.TICKET_TYPES
        context['selected_ticket_type'] = self.request.GET.get('ticket_type', '')
        context['selected_student_group'] = self.request.GET.get('student_group', '')
        context['bus_records'] = BusRecord.objects.filter(org=self.request.user.profile.org)
        context['selected_pickup_bus'] = self.request.GET.get('pickup_bus', '')
        context['selected_drop_bus'] = self.request.GET.get('drop_bus', '')
        context['schedules'] = Schedule.objects.filter(org=self.request.user.profile.org)
        context['selected_pickup_schedule'] = self.request.GET.get('pickup_schedule', '')
        context['selected_drop_schedule'] = self.request.GET.get('drop_schedule', '')
        context['stops'] = Stop.objects.filter(org=self.request.user.profile.org, registration=self.registration).order_by('name')
        context['selected_pickup_stop'] = self.request.GET.get('pickup_stop', '')
        context['selected_drop_stop'] = self.request.GET.get('drop_stop', '')
        
        # Preserve query parameters for pagination
        query_dict = self.request.GET.copy()
        if 'page' in query_dict:
            query_dict.pop('page')
        context['query_params'] = query_dict.urlencode()
        
        return context


class TicketFilterExportView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to handle ticket export requests from the filter page for central admin users.
    This view accepts POST requests to initiate the export of filtered ticket data to an Excel file.
    It extracts filtering parameters from the request exactly as TicketFilterView does,
    triggers an asynchronous Celery task (export_filtered_tickets_to_excel) to perform the export,
    and returns a JSON response indicating that the export request has been received.
    """
    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        registration_slug = self.kwargs.get('registration_slug')
        
        logger.info(f"TicketFilterExportView POST request - registration: {registration_slug}")
        logger.info(f"GET parameters: {request.GET.dict()}")
        
        # Extract filters exactly as TicketFilterView.get_queryset() does
        filters = {
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date'),
            'institution': request.GET.get('institution'),
            'ticket_type': request.GET.get('ticket_type'),
            'student_group': request.GET.get('student_group'),
            'pickup_bus': request.GET.get('pickup_bus'),
            'drop_bus': request.GET.get('drop_bus'),
            'pickup_schedule': request.GET.get('pickup_schedule'),
            'drop_schedule': request.GET.get('drop_schedule'),
            'pickup_stop': request.GET.get('pickup_stop'),
            'drop_stop': request.GET.get('drop_stop'),
        }

        logger.info(f"Filters being sent to Celery task: {filters}")
        
        # Trigger the new dedicated Celery task
        export_filtered_tickets_to_excel.apply_async(
            args=[request.user.id, registration_slug, filters]
        )

        return JsonResponse({"message": "Export request received. You will be notified once the export is ready."})


class FAQCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new FAQ entry associated with a specific registration.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the view logic for creating a new object.
    Attributes:
        template_name (str): Path to the template used to render the form.
        model (FAQ): The model class to create an instance of.
        form_class (FAQForm): The form class used for input validation and rendering.
    Methods:
        form_valid(form):
            Handles valid form submission. Associates the new FAQ with the current user's organization
            and the specified registration, then saves the FAQ instance.
        get_success_url():
            Returns the URL to redirect to after successful creation, pointing to the registration update view.
    """
    template_name = 'central_admin/registration_create.html'
    model = FAQ
    form_class = FAQForm
    
    def form_valid(self, form):
        faq = form.save(commit=False)
        user = self.request.user
        faq.org = user.profile.org
        faq.registration = get_object_or_404(Registration, slug=self.kwargs['registration_slug'])
        faq.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
    
    
class FAQDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for deleting an FAQ entry in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DeleteView: Provides the delete object functionality.
    Attributes:
        model (FAQ): The FAQ model to be deleted.
        template_name (str): Template used to confirm deletion.
        slug_url_kwarg (str): URL keyword argument for the FAQ slug.
    Methods:
        get_success_url():
            Returns the URL to redirect to after successful deletion,
            specifically the registration update page for the relevant registration.
    """
    model = FAQ
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_url_kwarg = 'faq_slug'
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
    

class ScheduleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for listing Schedule objects associated with a specific Registration and organization.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality for Schedule objects.
    Attributes:
        model (Schedule): The model to list.
        template_name (str): The template used to render the schedule list.
        context_object_name (str): The context variable name for the list of schedules.
    Methods:
        get_queryset(self):
            Retrieves the queryset of Schedule objects filtered by the current user's organization and the specified registration slug.
        get_context_data(self, **kwargs):
            Adds the registration object to the context for template rendering.
    """
    model = Schedule
    template_name = 'central_admin/schedule_list.html'
    context_object_name = 'schedules'
    
    def get_queryset(self):
        self.registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = Schedule.objects.filter(org=self.request.user.profile.org, registration=self.registration)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = self.registration
        return context


class ScheduleCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new Schedule instance associated with a specific Registration.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the view logic for creating a model instance.
    Attributes:
        model (Schedule): The model class to create.
        template_name (str): The template used to render the view.
        form_class (ScheduleForm): The form class used for creating a Schedule.
    Methods:
        form_valid(form):
            Associates the new Schedule with the current user's organization and the specified Registration.
            Saves the Schedule instance and proceeds with the default form_valid behavior.
        get_context_data(**kwargs):
            Adds the relevant Registration object to the context for template rendering.
        get_success_url():
            Returns the URL to redirect to after successful creation, passing the registration_slug as a URL parameter.
    """
    model = Schedule
    template_name = 'central_admin/schedule_create.html'
    form_class = ScheduleForm
    
    def form_valid(self, form):
        schedule = form.save(commit=False)
        schedule.org = self.request.user.profile.org
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        schedule.registration = registration
        schedule.save()
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:schedule_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class ScheduleUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View for updating a Schedule instance in the central admin interface.
    Inherits from:
        - LoginRequiredMixin: Ensures the user is authenticated.
        - CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        - UpdateView: Provides update functionality for a model instance.
    Attributes:
        model (Schedule): The model to be updated.
        template_name (str): Path to the template used to render the update form.
        form_class (ScheduleForm): The form class used for updating the Schedule.
        slug_url_kwarg (str): The keyword argument for the schedule's slug in the URL.
    Methods:
        get_context_data(self, **kwargs):
            Adds the related Registration object to the context using the 'registration_slug' from the URL.
        get_success_url(self):
            Returns the URL to redirect to after a successful update, using the 'registration_slug' from the URL.
    """
    model = Schedule
    template_name = 'central_admin/schedule_update.html'
    form_class = ScheduleForm
    slug_url_kwarg = 'schedule_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context
            
    def get_success_url(self):
        return reverse('central_admin:schedule_list', kwargs={'registration_slug': self.kwargs['registration_slug']})


class ScheduleGroupListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for listing ScheduleGroup objects associated with a specific Registration.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality for ScheduleGroup objects.
    Attributes:
        model (ScheduleGroup): The model to list.
        template_name (str): Template used for rendering the list.
        context_object_name (str): Name of the context variable for the list.
    Methods:
        get_queryset():
            Retrieves ScheduleGroup objects filtered by the registration specified in the URL kwargs.
        get_context_data(**kwargs):
            Adds the current Registration object to the context for template rendering.
    """
    model = ScheduleGroup
    template_name = 'central_admin/schedule_group_list.html'
    context_object_name = 'schedule_groups'
    
    def get_queryset(self):
        self.registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = ScheduleGroup.objects.filter(registration=self.registration)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = self.registration
        return context
    

class ScheduleGroupCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View for creating a new ScheduleGroup associated with a specific Registration.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        CreateView: Provides the view logic for creating a model instance.
    Attributes:
        model (ScheduleGroup): The model to be created.
        template_name (str): The template used for rendering the form.
        form_class (ScheduleGroupForm): The form class used for input validation and rendering.
    Methods:
        form_valid(form):
            Associates the new ScheduleGroup with the Registration specified by the 'registration_slug' URL parameter,
            saves the instance, and proceeds with the default form_valid behavior.
        get_context_data(**kwargs):
            Adds the relevant Registration instance to the context for template rendering.
        get_success_url():
            Returns the URL to redirect to after successful creation, pointing to the schedule group list for the current registration.
    """
    model = ScheduleGroup
    template_name = 'central_admin/schedule_group_create.html'
    form_class = ScheduleGroupForm
    
    def form_valid(self, form):
        schedule_group = form.save(commit=False)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        schedule_group.registration = registration
        schedule_group.save()
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration']=Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context    
    def get_success_url(self):
        return reverse('central_admin:schedule_group_list', kwargs={'registration_slug': self.kwargs['registration_slug']})

    
class MoreMenuView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    template_name = 'central_admin/more_menu.html'


class BusRequestListView(ListView):
    """
    Displays a paginated list of bus requests for a specific registration and organization in the central admin interface.
    Attributes:
        model (BusRequest): The model associated with this view.
        template_name (str): The template used to render the bus request list.
        context_object_name (str): The name of the context variable for the bus requests.
        paginate_by (int): Number of bus requests to display per page.
    Methods:
        get_queryset(self):
            Returns a queryset of BusRequest objects filtered by the current user's organization and the specified registration.
        get_context_data(self, **kwargs):
            Extends the context with:
                - The current registration object.
                - The total number of bus requests for the organization and registration.
                - The number of open and closed requests.
                - A flag for each bus request indicating if a ticket exists for its receipt.
    """
    model = BusRequest
    template_name = 'central_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, registration=registration).order_by('-created_at')
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(student_name__icontains=search_query) |
                Q(contact_no__icontains=search_query) |
                Q(contact_email__icontains=search_query) |
                Q(receipt__receipt_id__icontains=search_query)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt,
                is_terminated=False
            ).exists()
        context["search_query"] = self.request.GET.get('search', '').strip()
        return context

class BusRequestOpenListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for displaying a paginated list of open bus requests for a specific registration in the central admin panel.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (BusRequest): The model to list.
        template_name (str): Template used for rendering the list.
        context_object_name (str): Name of the context variable for the
        paginate_by (int): Number of items per page.
    Methods:
        get_queryset(self):
            Returns a queryset of open BusRequest objects filtered by the current user's organization,
            the specified registration (by slug), and status 'open', ordered by creation date descending.
        get_context_data(self, **kwargs):
            Extends context with:
                - registration: The Registration instance for the given slug.
                - total_requests: Total number of BusRequest objects for the org and registration.
                - open_requests: Number of open BusRequest objects.
                - closed_requests: Number of closed BusRequest objects.
                - For each bus request in the page, adds 'has_ticket' attribute indicating if a Ticket exists
                  for the registration and the request's receipt.
    """
    model = BusRequest
    template_name = 'central_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, registration=registration, status='open').order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org,  
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org,  
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt,
                is_terminated=False
            ).exists()
        return context

class BusRequestClosedListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View for displaying a paginated list of closed bus requests for a specific registration in the central admin interface.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        ListView: Provides list display functionality.
    Attributes:
        model (BusRequest): The model to list.
        template_name (str): Template used for rendering the list.
        context_object_name (str): Name of the context variable for the queryset.
        paginate_by (int): Number of items per page.
    Methods:
        get_queryset(self):
            Returns a queryset of closed BusRequest objects filtered by the current user's organization and the specified registration.
        get_context_data(self, **kwargs):
            Adds additional context including:
                - The current registration object.
                - Total, open, and closed request counts for the registration and organization.
                - For each bus request, a boolean 'has_ticket' indicating if a ticket exists for the request's receipt.
    """
    model = BusRequest
    template_name = 'central_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, registration=registration, status='closed').order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["registration"] = registration
        context["total_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration
        ).count()
        context["open_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration, 
            status='open'
        ).count()
        context["closed_requests"] = BusRequest.objects.filter(
            org=self.request.user.profile.org, 
            registration=registration, 
            status='closed'
        ).count()
        for request in context["bus_requests"]:
            request.has_ticket = Ticket.objects.filter(
                registration=registration, 
                recipt=request.receipt
            ).exists()
        return context

class BusRequestDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    """
    View for handling the deletion of BusRequest objects by central admin users.
    Inherits from:
        LoginRequiredMixin: Ensures the user is authenticated.
        CentralAdminOnlyAccessMixin: Restricts access to central admin users.
        DeleteView: Provides the delete functionality for a Django model.
    Attributes:
        model (BusRequest): The model to be deleted.
        template_name (str): Template used to confirm deletion.
        slug_field (str): The field used to identify the object in the URL.
        slug_url_kwarg (str): The URL keyword argument for the slug.
    Methods:
        get_context_data(self, **kwargs):
            Adds the 'registration' attribute of the BusRequest object to the context.
        get_success_url(self):
            Returns the URL to redirect to after successful deletion, using the 'registration_slug' from the URL kwargs.
    """
    model = BusRequest
    template_name = 'central_admin/bus_request_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'bus_request_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.object.registration
        return context
    
    def get_success_url(self):
        return reverse('central_admin:bus_request_list', kwargs={'registration_slug': self.kwargs['registration_slug']})


class BusSearchFormView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, FormView):
    """
    View for handling the bus search form in the central admin interface.
    This view allows central admin users to search for bus schedules and stops associated with a specific registration.
    It ensures that only authenticated users with central admin access can use the form. The view dynamically filters
    the available stops based on the registration code provided in the URL, and stores the selected stop and schedule
    in the session upon successful form submission. The context is enriched with registration details and the type of
    change (pickup or drop) based on query parameters. Upon successful form submission, the user is redirected to the
    bus search results page with relevant query parameters.
    Attributes:
        template_name (str): The template used to render the form.
        form_class (Form): The form class used for bus searching.
    Methods:
        get_registration(): Retrieves the Registration object based on the registration code from the URL.
        get_form(form_class=None): Returns the form instance with the 'stop' queryset filtered by registration.
        form_valid(form): Handles valid form submission, storing selected stop and schedule in the session.
        get_context_data(**kwargs): Adds registration and change type information to the template context.
        get_success_url(): Constructs the URL to redirect to after successful form submission, including query parameters.
    """
    template_name = 'central_admin/bus_search_form.html'
    form_class = BusSearchForm

    def get_registration(self):
        """Fetch registration using the code from the URL."""
        registration_code = self.kwargs.get('registration_code')
        return get_object_or_404(Registration, code=registration_code)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        registration = self.get_registration()
        form.fields['stop'].queryset = registration.stops.all()
        return form

    def form_valid(self, form):
        stop = form.cleaned_data['stop']
        schedule = form.cleaned_data['schedule']
        self.request.session['stop_id'] = stop.id
        self.request.session['schedule_id'] = schedule.id
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        
        change_type = self.request.GET.get('changeType')  
        
        if change_type == 'pickup':
            context['change_type'] = 'pickup'
        elif change_type == 'drop':
            context['change_type'] = 'drop'
        
        return context

    def get_success_url(self):
        registration_code = self.get_registration().code
        change_type = self.request.GET.get('changeType') 
        ticket_id = self.kwargs.get('ticket_id')
        query_params = {'changeType': change_type}
        search_result_base_url = reverse('central_admin:bus_search_results', kwargs={'ticket_id': ticket_id, 'registration_code': registration_code})
        return f"{search_result_base_url}?{urlencode(query_params)}"


class BusSearchResultsView(ListView):
    """
    View to display available bus records for a given registration, stop, and schedule, filtered by change type (pickup or drop).
    This view retrieves bus records that match the user's registration, selected stop, and schedule, and ensures that the number of bookings does not exceed the bus capacity for either pickup or drop, depending on the requested change type. The results are annotated with the number of available seats and provided to the template for display.
    Context:
        bus_records: Queryset of filtered and annotated BusRecord instances.
        registration: The Registration instance corresponding to the registration code in the URL.
        stop: The Stop instance corresponding to the stop_id from the session.
        schedule: The Schedule instance corresponding to the schedule_id from the session.
        ticket: The Ticket instance corresponding to the ticket_id in the URL.
        change_type: The type of change requested ('pickup' or 'drop').
    Methods:
        get_queryset(): Returns a queryset of BusRecord objects filtered and annotated based on registration, stop, schedule, and change type.
        get_context_data(**kwargs): Adds registration, stop, schedule, ticket, and change_type to the context.
    """
    template_name = 'central_admin/bus_search_results.html'
    context_object_name = 'bus_records'

    def get_queryset(self):
        # Retrieve the registration based on the registration code
        registration_code = self.kwargs.get('registration_code')
        registration = get_object_or_404(Registration, code=registration_code)

        # Get stop and schedule from session
        self.stop_id = self.request.session.get('stop_id')
        self.schedule_id = self.request.session.get('schedule_id')
        self.change_type = self.request.GET.get('changeType')

        # Return empty queryset if required data is missing
        if not (self.stop_id and self.schedule_id):
            return BusRecord.objects.none()

        # Initialize buses with an empty queryset
        buses = BusRecord.objects.none()

        # Filter logic based on changeType
        if self.change_type == 'pickup':
            buses = BusRecord.objects.filter(
                org=registration.org,
                registration=registration,
                schedule_id=self.schedule_id,
                pickup_booking_count__lt=F('bus__capacity'),  # Pickup count must be less than capacity
                route__stops__id=self.stop_id,  # Stop must be in the route
            ).annotate(available_seats=F('bus__capacity') - F('pickup_booking_count'))
        elif self.change_type == 'drop':
            buses = BusRecord.objects.filter(
                org=registration.org,
                registration=registration,
                schedule_id=self.schedule_id,
                drop_booking_count__lt=F('bus__capacity'),  # Drop count must be less than capacity
                route__stops__id=self.stop_id,  # Stop must be in the route
            ).annotate(available_seats=F('bus__capacity') - F('drop_booking_count'))

        return buses.distinct()

    def get_context_data(self, **kwargs):
        """Include additional context like the registration."""
        context = super().get_context_data(**kwargs)
        context['registration'] = get_object_or_404(Registration, code=self.kwargs.get('registration_code'))
        context['stop'] = get_object_or_404(Stop, id=self.stop_id)
        context['schedule'] = get_object_or_404(Schedule, id=self.schedule_id)
        context['ticket'] = get_object_or_404(Ticket, ticket_id=self.kwargs.get('ticket_id'))
        context['change_type'] = self.change_type
        return context
    

class UpdateBusInfoView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View for updating the bus information (pickup or drop) associated with a ticket for a given registration.
    This view allows central admin users to change the assigned bus record and stop for either pickup or drop for a specific ticket.
    It ensures that booking counts on the involved BusRecord instances are updated accordingly and prevents negative booking counts.
    Methods:
        get(request, registration_code, ticket_id, bus_record_slug):
            Handles GET requests to update the pickup or drop bus record and stop for a ticket.
            - Retrieves the relevant Registration, Ticket, and Stop objects.
            - Determines the type of change ('pickup' or 'drop') from the request.
            - Updates the booking counts on the old and new BusRecord instances.
            - Updates the ticket's pickup/drop bus record and stop.
            - Redirects to the ticket list view for the registration.
    Decorators:
        @transaction.atomic: Ensures all database operations within the method are atomic.
    Access:
        - Requires the user to be logged in and have central admin access.
    """
    @transaction.atomic
    def get(self, request, registration_code, ticket_id, bus_record_slug):
        registration = get_object_or_404(Registration, code=registration_code)
        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        
        change_type = self.request.GET.get('changeType')
        
        stop_id = self.request.session.get('stop_id')
        
        stop = get_object_or_404(Stop, id=stop_id)
        
        if change_type == 'pickup':
            new_bus_record = get_object_or_404(BusRecord, slug=bus_record_slug)
            current_pickup_bus_record = ticket.pickup_bus_record

            # If the new bus record is different from the current one, update counts
            if new_bus_record != current_pickup_bus_record:
                if current_pickup_bus_record.pickup_booking_count > 0:
                    current_pickup_bus_record.pickup_booking_count -= 1
                    current_pickup_bus_record.save()
                else:
                    # Optionally, log this or raise an error to avoid accidental negative counts
                    print("Warning: Pickup booking count cannot go negative!")
                    
                new_bus_record.pickup_booking_count += 1
                new_bus_record.save()

            ticket.pickup_bus_record = new_bus_record
            ticket.pickup_point = stop
            ticket.save()

            
        if change_type == 'drop':
            new_bus_record = get_object_or_404(BusRecord, slug=bus_record_slug)
            current_drop_bus_record = ticket.drop_bus_record

            if new_bus_record != current_drop_bus_record:
                if current_drop_bus_record:
                    print("Current bus count (before decrement):", current_drop_bus_record.drop_booking_count)
                    current_drop_bus_record.drop_booking_count -= 1
                    current_drop_bus_record.save()
                    print("Current bus count (after decrement):", current_drop_bus_record.drop_booking_count)

                print("New bus count (before increment):", new_bus_record.drop_booking_count)
                new_bus_record.drop_booking_count += 1
                new_bus_record.save()
                print("New bus count (after increment):", new_bus_record.drop_booking_count)

            ticket.drop_bus_record = new_bus_record
            ticket.drop_point = stop
            ticket.save()
        
        return redirect(
            reverse('central_admin:ticket_list', 
                    kwargs={'registration_slug': registration.slug}
                )
            )


class BusRequestStatusUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to handle status updates for BusRequest objects by central admin users.

    POST:
        - Toggles the status of a BusRequest between 'open' and 'closed'.
        - Optionally creates a BusRequestComment if a comment is provided in the POST data.
        - Renders and returns the updated modal body HTML for the bus request.
        - Sets the 'HX-Trigger' header to 'reloadPage' to notify the frontend to reload the page.

    Permissions:
        - User must be authenticated and have central admin access.

    Args:
        request (HttpRequest): The HTTP request object.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments, expects 'bus_request_slug' to identify the BusRequest.

    Returns:
        HttpResponse: Contains the rendered modal body HTML and triggers a page reload on the frontend.
    """
    def post(self, request, *args, **kwargs):
        bus_request = get_object_or_404(BusRequest, slug=self.kwargs['bus_request_slug'])
        new_status = 'open' if bus_request.status == 'closed' else 'closed'
        comment_text = request.POST.get('comment')
        bus_request.status = new_status
        bus_request.save()
        if comment_text:
            BusRequestComment.objects.create(
                bus_request=bus_request,
                comment=comment_text,
                created_by=request.user
            )
        modal_body_html = render_to_string('central_admin/bus_request_modal_body.html', {'bus_request': bus_request})
        response = HttpResponse(modal_body_html)
        response['HX-Trigger'] = 'reloadPage'
        return response

class BusRequestCommentView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to handle the creation of comments on bus requests by central admin users.

    Methods:
        post(request, *args, **kwargs):
            Handles POST requests to create a new comment for a specific bus request.
            - Retrieves the BusRequest instance using the provided slug.
            - Validates the submitted comment form.
            - If valid, creates a new BusRequestComment associated with the bus request and the current user.
            - Renders the new comment as HTML and returns it in the response.
            - Returns a 400 response if the form is invalid.

    Permissions:
        - Requires the user to be authenticated and have central admin access.
    """
    def post(self, request, *args, **kwargs):
        bus_request = get_object_or_404(BusRequest, slug=self.kwargs['bus_request_slug'])
        comment_form = BusRequestCommentForm(request.POST)
        if comment_form.is_valid():
            comment = BusRequestComment.objects.create(
                bus_request=bus_request,
                comment=comment_form.cleaned_data['comment'],
                created_by=request.user
            )
            comment_html = render_to_string('central_admin/comment.html', {'comment': comment}).strip()
            return HttpResponse(comment_html)
        return HttpResponse('Invalid form submission', status=400)


class TicketExportView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to handle ticket export requests for central admin users.
    This view accepts POST requests to initiate the export of ticket data to an Excel file.
    It extracts filtering parameters from the request, triggers an asynchronous Celery task
    (`export_tickets_to_excel`) to perform the export, and returns a JSON response indicating
    that the export request has been received.
    """
    def post(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        search_term = request.GET.get('search', '')
        filters = {
            'institution': request.GET.get('institution'),
            'pickup_points': request.GET.getlist('pickup_point'),
            'drop_points': request.GET.getlist('drop_point'),
            'schedule': request.GET.get('schedule'),
            'pickup_buses': request.GET.getlist('pickup_bus'),
            'drop_buses': request.GET.getlist('drop_bus'),
            'student_group': request.GET.get('student_group'),
            'pickup_schedule': request.GET.get('pickup_schedule'),
            'drop_schedule': request.GET.get('drop_schedule'),  
        }

        # Trigger the Celery task
        export_tickets_to_excel.apply_async(
            args=[request.user.id, registration_slug, search_term, filters]
        )

        return JsonResponse({"message": "Export request received. You will be notified once the export is ready."})


class StudentGroupFilterView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to filter and retrieve student groups for a given institution.

    This view requires the user to be authenticated and have central admin access.
    It handles GET requests, extracting the 'institution' slug from the query parameters.
    If an institution slug is provided, it fetches and orders the related StudentGroup objects by name.
    The resulting student groups are rendered in the 'central_admin/partials/student_group_options.html' template.

    Args:
        request (HttpRequest): The HTTP request object.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments.

    Returns:
        HttpResponse: Rendered HTML with the filtered student groups.
    """
    def get(self, request, *args, **kwargs):
        institution_slug = request.GET.get('institution')
        student_groups = StudentGroup.objects.filter(institution__slug=institution_slug).order_by('name') if institution_slug else []
        return render(request, 'central_admin/partials/student_group_options.html', {'student_groups': student_groups})


class GenerateStudentPassView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to handle the generation of student passes by central admin users.
    This view accepts POST requests and triggers an asynchronous Celery task to generate student passes
    based on the provided filters. The filters can include start and end dates, institution, ticket type,
    and student group. The user initiating the request must be authenticated and have central admin access.
    Attributes:
        None
    Methods:
        post(request, *args, **kwargs):
            Handles POST requests to initiate the student pass generation process.
            Extracts filter parameters from the request, triggers the Celery task, and returns a JSON response
            indicating that the request has been received.
    """
    def post(self, request, *args, **kwargs):
        registration_slug = self.kwargs.get('registration_slug')
        filters = {
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date'),
            'institution': request.GET.get('institution'),
            'ticket_type': request.GET.get('ticket_type'),
            'student_group': request.GET.get('student_group'),
            'pickup_stop': request.GET.get('pickup_stop'),
            'drop_stop': request.GET.get('drop_stop'),
        }

        # Trigger the Celery task
        generate_student_pass.apply_async(
            args=[request.user.id, registration_slug, filters]
        )

        return JsonResponse({"message": "Student pass generation request received. You will be notified once the passes are ready."})


class StudentPassFileDownloadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View for downloading a student's pass file.

    This view allows central admin users to download a file associated with a student pass.
    It requires the user to be authenticated and have central admin access.

    Methods
    -------
    get(request, *args, **kwargs):
        Handles GET requests to retrieve and download the specified student pass file as an attachment.
        - Retrieves the StudentPassFile object using the 'slug' from the URL.
        - Returns a FileResponse to prompt the user to download the file.
    """
    def get(self, request, *args, **kwargs):
        student_pass_file = get_object_or_404(StudentPassFile, slug=self.kwargs['slug'])
        return FileResponse(student_pass_file.file, as_attachment=True, filename=student_pass_file.file.name)


class StopTransferView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, RegistrationClosedOnlyAccessMixin, View):
    """
    View to transfer a stop to a new route and update all related tickets.
    """
    template_name = 'central_admin/stop_transfer.html'

    def get(self, request, registration_slug, route_slug, stop_slug):
        registration = get_object_or_404(Registration, slug=registration_slug)
        stop = get_object_or_404(Stop, slug=stop_slug, registration=registration)
        form = StopTransferForm(org=request.user.profile.org, registration=registration)
        return render(request, self.template_name, {
            'form': form,
            'stop': stop,
            'registration': registration,
        })

    def post(self, request, registration_slug, route_slug, stop_slug):
        registration = get_object_or_404(Registration, slug=registration_slug)
        stop = get_object_or_404(Stop, slug=stop_slug, registration=registration)
        form = StopTransferForm(request.POST, org=request.user.profile.org, registration=registration)
        if form.is_valid():
            new_route = form.cleaned_data['new_route']
            try:
                move_stop_and_update_tickets(stop, new_route)
                messages.success(request, f"Stop '{stop.name}' transferred to route '{new_route.name}' and tickets updated.")
                return redirect('central_admin:stop_list', registration_slug=registration.slug, route_slug=new_route.slug)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        return render(request, self.template_name, {
            'form': form,
            'stop': stop,
            'registration': registration,
        })

class BusRecordExportPDFView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    def get(self, request, registration_slug):
        registration = get_object_or_404(Registration, slug=registration_slug)
        bus_records = BusRecord.objects.filter(
            org=request.user.profile.org, registration=registration
        ).order_by('label')

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Margins and layout
        margin_left, margin_right = 40, 40
        margin_top, margin_bottom = 60, 60
        usable_width = width - margin_left - margin_right
        y = height - margin_top

        # Title (only on first page)
        p.setFont("Helvetica-Bold", 20)
        p.setFillColorRGB(0.13, 0.22, 0.38)
        p.drawString(margin_left, y, f"Bus Records for {registration.name}")
        y -= 30

        # Subtitle (only on first page)
        p.setFont("Helvetica-Bold", 12)
        p.setFillColorRGB(0.25, 0.25, 0.25)
        p.drawString(margin_left, y, f"Total Records: {bus_records.count()}")
        y -= 20

        # Horizontal line
        p.setStrokeColorRGB(0.18, 0.32, 0.55)
        p.setLineWidth(1.5)
        p.line(margin_left, y, width - margin_right, y)
        y -= 16

        # Table settings
        row_height, header_height = 22, 25
        font_size, header_font_size = 10, 11

        # Main headers (3 columns, full width)
        main_headers = ["Label", "Registration No", "Capacity"]
        main_col_widths = [
            int(usable_width * 0.45),
            int(usable_width * 0.40),
            int(usable_width * 0.15),
        ]
        main_col_x = [margin_left]
        for w in main_col_widths[:-1]:
            main_col_x.append(main_col_x[-1] + w)
        main_col_x.append(margin_left + sum(main_col_widths))

        # Trip headers (3 columns, full width, slight indent)
        trip_headers = ["Schedule", "Route", "Bookings"]
        trip_col_widths = [
            int(usable_width * 0.45),
            int(usable_width * 0.40),
            int(usable_width * 0.15),
        ]
        trip_col_x = [margin_left]
        for w in trip_col_widths[:-1]:
            trip_col_x.append(trip_col_x[-1] + w)
        trip_col_x.append(margin_left + sum(trip_col_widths))

        def draw_main_header(y):
            p.setFont("Helvetica-Bold", header_font_size)
            p.setFillColorRGB(0.19, 0.32, 0.55)
            p.rect(margin_left, y - header_height + 6, usable_width, header_height, fill=1, stroke=0)
            p.setFillColorRGB(1, 1, 1)
            for i, h in enumerate(main_headers):
                p.drawString(main_col_x[i] + 8, y - header_height + 16, h)
            p.setStrokeColorRGB(0.18, 0.32, 0.55)
            p.setLineWidth(1)
            p.line(margin_left, y - header_height + 6, margin_left + usable_width, y - header_height + 6)
            return y - header_height

        def draw_main_row(y, values):
            p.setFont("Helvetica", font_size)
            p.setFillColorRGB(0.97, 0.98, 1)
            p.rect(margin_left, y - row_height + 6, usable_width, row_height, fill=1, stroke=0)
            p.setFillColorRGB(0.13, 0.22, 0.38)
            for i, val in enumerate(values):
                p.drawString(main_col_x[i] + 8, y - row_height + 14, str(val))
            p.setStrokeColorRGB(0.85, 0.85, 0.9)
            p.setLineWidth(0.5)
            p.line(margin_left, y - row_height + 6, margin_left + usable_width, y - row_height + 6)
            return y - row_height

        def draw_trip_header(y):
            p.setFont("Helvetica-Bold", header_font_size)
            p.setFillColorRGB(0.82, 0.89, 0.98)
            p.rect(margin_left, y - header_height + 6, usable_width, header_height, fill=1, stroke=0)
            p.setFillColorRGB(0.13, 0.22, 0.38)
            for i, h in enumerate(trip_headers):
                p.drawString(trip_col_x[i] + 8, y - header_height + 16, h)
            p.setStrokeColorRGB(0.18, 0.32, 0.55)
            p.setLineWidth(0.7)
            p.line(margin_left, y - header_height + 6, margin_left + usable_width, y - header_height + 6)
            return y - header_height

        def draw_trip_row(y, values):
            p.setFont("Helvetica", font_size)
            p.setFillColorRGB(1, 1, 1)
            p.rect(margin_left, y - row_height + 6, usable_width, row_height, fill=1, stroke=0)
            p.setFillColorRGB(0.13, 0.22, 0.38)
            for i, val in enumerate(values):
                p.drawString(trip_col_x[i] + 8, y - row_height + 14, str(val))
            p.setStrokeColorRGB(0.85, 0.85, 0.9)
            p.setLineWidth(0.5)
            p.line(margin_left, y - row_height + 6, margin_left + usable_width, y - row_height + 6)
            return y - row_height

        # Only redraw table headers on new pages, not the title/subtitle
        def redraw_page_header(y):
            return y  # No-op, as we don't want to redraw title/subtitle

        first_page = True

        for record in bus_records:
            trips = list(record.trips.select_related('schedule', 'route').all())
            trip_count = max(1, len(trips))
            needed_space = row_height + header_height + trip_count * row_height + 30
            if y < margin_bottom + needed_space:
                p.showPage()
                y = height - margin_top
                # Only redraw table headers, not title/subtitle
                first_page = False

            reg_no = record.bus.registration_no if record.bus else "----"
            cap = str(record.bus.capacity) if record.bus else "----"
            y = draw_main_header(y)
            y = draw_main_row(y, [record.label, reg_no, cap])
            y = draw_trip_header(y)

            if trips:
                for trip in trips:
                    if y < margin_bottom + row_height + 20:
                        p.showPage()
                        y = height - margin_top
                        # Only redraw table headers, not title/subtitle
                        y = draw_main_header(y)
                        y = draw_main_row(y, [record.label, reg_no, cap])
                        y = draw_trip_header(y)
                    y = draw_trip_row(
                        y,
                        [
                            trip.schedule.name if trip.schedule else "----",
                            trip.route.name if trip.route else "----",
                            getattr(trip, "booking_count", "----"),
                        ],
                    )
            else:
                if y < margin_bottom + row_height + 20:
                    p.showPage()
                    y = height - margin_top
                    y = draw_main_header(y)
                    y = draw_main_row(y, [record.label, reg_no, cap])
                    y = draw_trip_header(y)
                y = draw_trip_row(y, ["No trips", "", ""])

            y -= 20  # Space between bus records

        # Footer
        p.setFont("Helvetica-Oblique", 9)
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.drawRightString(
            width - margin_right,
            margin_bottom - 30,
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
        p.setFillColorRGB(0, 0, 0)
        p.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"bus_records_{registration.slug}.pdf",
        )


class ReservationListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    """
    ReservationListView displays the list of reservations for central admin users.
    Also provides driver payment summary by month in a separate tab.
    
    This view inherits from:
        - LoginRequiredMixin: Ensures that the user is authenticated.
        - CentralAdminOnlyAccessMixin: Ensures that the user has central admin access.
        - TemplateView: Renders a template with the given context.
    
    Attributes:
        template_name (str): The template to render for this view.
    """
    template_name = "central_admin/reservation_list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get month filter from query params or default to current month
        from datetime import datetime
        month_param = self.request.GET.get('month')
        if month_param:
            try:
                filter_date = datetime.strptime(month_param, '%Y-%m')
                year = filter_date.year
                month = filter_date.month
                context['current_month'] = month_param
            except ValueError:
                year = datetime.now().year
                month = datetime.now().month
                context['current_month'] = f"{year}-{month:02d}"
        else:
            year = None
            month = None
            context['current_month'] = ""
        
        # Get reservations with optional filters
        reservations_query = BusReservationRequest.objects.filter(
            org=self.request.user.profile.org
        ).select_related('institution', 'created_by').order_by('-created_at')
        
        # Apply month filter if provided
        if month_param and year and month:
            reservations_query = reservations_query.filter(
                created_at__year=year,
                created_at__month=month
            )
        
        # Apply status filter if provided
        status_param = self.request.GET.get('status')
        if status_param and status_param in ['pending', 'approved', 'rejected']:
            reservations_query = reservations_query.filter(status=status_param)
        
        context['reservations'] = reservations_query
        context['status_filter'] = status_param
        context['month_filter'] = month_param
        
        # Set year and month for driver payments calculation
        if not year or not month:
            year = datetime.now().year
            month = datetime.now().month
            context['current_month'] = f"{year}-{month:02d}"
        
        # Calculate driver payments for the selected month
        from django.db.models import Sum, Count, Q
        from core.models import User
        
        # Get all trip expenses for the month
        trip_expenses = TripExpense.objects.filter(
            bus_assignment__reservation_request__org=self.request.user.profile.org,
            recorded_at__year=year,
            recorded_at__month=month
        ).select_related('bus_assignment__driver__profile')
        
        # Aggregate by driver
        driver_payments = {}
        for expense in trip_expenses:
            driver = expense.bus_assignment.driver
            if driver.id not in driver_payments:
                driver_payments[driver.id] = {
                    'driver_id': driver.id,
                    'driver_name': f"{driver.profile.first_name} {driver.profile.last_name}",
                    'driver_email': driver.email,
                    'trip_count': 0,
                    'total_bonus': 0,
                    'total_expenses': 0,
                }
            driver_payments[driver.id]['trip_count'] += 1
            driver_payments[driver.id]['total_bonus'] += float(expense.driver_bonus)
            driver_payments[driver.id]['total_expenses'] += float(expense.total_expense)
        
        context['driver_payments'] = list(driver_payments.values())
        context['total_trips'] = sum(p['trip_count'] for p in driver_payments.values())
        context['total_bonus'] = sum(p['total_bonus'] for p in driver_payments.values())
        context['total_expenses'] = sum(p['total_expenses'] for p in driver_payments.values())
        
        return context

class ReservationDetailView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    """
    ReservationDetailView displays the details of a specific reservation for central admin users.
    """
    template_name = "central_admin/reservation_detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reservation'] = get_object_or_404(
            BusReservationRequest,
            slug=self.kwargs['slug'],
            org=self.request.user.profile.org
        )
        return context


class ReservationApproveView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to approve a bus reservation request.
    """
    def post(self, request, *args, **kwargs):
        reservation = get_object_or_404(
            BusReservationRequest,
            slug=self.kwargs['slug'],
            org=request.user.profile.org,
            status='pending'
        )
        
        reservation.status = 'approved'
        reservation.approved_by = request.user
        reservation.approved_at = timezone.now()
        reservation.save()
        
        messages.success(request, f"Reservation #{reservation.reservation_no} has been approved successfully!")
        return redirect('central_admin:reservation_detail', slug=reservation.slug)


class ReservationRejectView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to reject a bus reservation request with a reason.
    """
    def post(self, request, *args, **kwargs):
        reservation = get_object_or_404(
            BusReservationRequest,
            slug=self.kwargs['slug'],
            org=request.user.profile.org,
            status='pending'
        )
        
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, "Rejection reason is required!")
            return redirect('central_admin:reservation_detail', slug=reservation.slug)
        
        reservation.status = 'rejected'
        reservation.rejected_reason = rejection_reason
        reservation.save()
        
        messages.success(request, f"Reservation #{reservation.reservation_no} has been rejected.")
        return redirect('central_admin:reservation_detail', slug=reservation.slug)


class BusAssignmentCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View to assign a bus to an approved reservation request.
    Only allows assignment to approved reservations.
    """
    model = BusReservationAssignment
    form_class = BusAssignmentForm
    template_name = 'central_admin/bus_assignment_create.html'
    
    def get_reservation(self):
        """Get the reservation request for this assignment."""
        return get_object_or_404(
            BusReservationRequest,
            slug=self.kwargs['slug'],
            org=self.request.user.profile.org,
            status='approved'
        )
    
    def get_form_kwargs(self):
        """Pass org and reservation_request to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['org'] = self.request.user.profile.org
        kwargs['reservation_request'] = self.get_reservation()
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add reservation to context."""
        context = super().get_context_data(**kwargs)
        context['reservation'] = self.get_reservation()
        return context
    
    def form_valid(self, form):
        """Save the bus assignment with the reservation and assigned_by user."""
        form.instance.reservation_request = self.get_reservation()
        form.instance.assigned_by = self.request.user
        
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f"Bus {form.instance.bus.registration_no} has been assigned successfully!"
            )
            return response
        except IntegrityError:
            messages.error(self.request, "This bus is already assigned to this reservation!")
            return redirect('central_admin:reservation_detail', slug=self.kwargs['slug'])
    
    def get_success_url(self):
        """Redirect back to the reservation detail page."""
        return reverse('central_admin:reservation_detail', kwargs={'slug': self.kwargs['slug']})


class BusAssignmentDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to remove a bus assignment from a reservation request.
    """
    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(
            BusReservationAssignment,
            id=self.kwargs['assignment_id'],
            reservation_request__org=request.user.profile.org
        )
        
        bus_reg_no = assignment.bus.registration_no
        reservation_slug = assignment.reservation_request.slug
        
        assignment.delete()
        
        messages.success(request, f"Bus {bus_reg_no} has been removed from this reservation.")
        return redirect('central_admin:reservation_detail', slug=reservation_slug)


class TripExpenseCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    """
    View to add trip expenses for a bus assignment.
    Allows recording fuel cost, toll charges, maintenance, driver bonus, and other expenses.
    """
    model = TripExpense
    form_class = TripExpenseForm
    template_name = 'central_admin/trip_expense_form.html'
    
    def get_bus_assignment(self):
        """Get the bus assignment for this expense."""
        return get_object_or_404(
            BusReservationAssignment,
            id=self.kwargs['assignment_id'],
            reservation_request__org=self.request.user.profile.org
        )
    
    def get_context_data(self, **kwargs):
        """Add bus assignment to context."""
        context = super().get_context_data(**kwargs)
        context['bus_assignment'] = self.get_bus_assignment()
        context['is_update'] = False
        return context
    
    def form_valid(self, form):
        """Save the trip expense with the bus assignment and recorded_by user."""
        form.instance.bus_assignment = self.get_bus_assignment()
        form.instance.recorded_by = self.request.user
        
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Trip expenses recorded successfully! Total: ₹{form.instance.total_expense}"
        )
        return response
    
    def get_success_url(self):
        """Redirect back to the reservation detail page."""
        return reverse('central_admin:reservation_detail', 
                      kwargs={'slug': self.get_bus_assignment().reservation_request.slug})


class TripExpenseUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    """
    View to update trip expenses for a bus assignment.
    """
    model = TripExpense
    form_class = TripExpenseForm
    template_name = 'central_admin/trip_expense_form.html'
    
    def get_object(self):
        """Get the trip expense to update."""
        return get_object_or_404(
            TripExpense,
            id=self.kwargs['pk'],
            bus_assignment__reservation_request__org=self.request.user.profile.org
        )
    
    def get_context_data(self, **kwargs):
        """Add bus assignment to context."""
        context = super().get_context_data(**kwargs)
        context['bus_assignment'] = self.object.bus_assignment
        context['is_update'] = True
        return context
    
    def form_valid(self, form):
        """Save the updated trip expense."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Trip expenses updated successfully! Total: ₹{form.instance.total_expense}"
        )
        return response
    
    def get_success_url(self):
        """Redirect back to the reservation detail page."""
        return reverse('central_admin:reservation_detail', 
                      kwargs={'slug': self.object.bus_assignment.reservation_request.slug})


class DriverPaymentDetailsView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, TemplateView):
    """
    View to display detailed trip information for a specific driver in a given month.
    Returns HTML fragment for modal display.
    """
    template_name = 'central_admin/driver_payment_details.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        driver_id = self.kwargs.get('driver_id')
        
        # Get driver
        driver = get_object_or_404(
            User,
            id=driver_id,
            profile__org=self.request.user.profile.org,
            profile__role=UserProfile.DRIVER
        )
        context['driver'] = driver
        
        # Get month filter
        from datetime import datetime
        month_param = self.request.GET.get('month')
        if month_param:
            try:
                filter_date = datetime.strptime(month_param, '%Y-%m')
                year = filter_date.year
                month = filter_date.month
            except ValueError:
                year = datetime.now().year
                month = datetime.now().month
        else:
            year = datetime.now().year
            month = datetime.now().month
        
        # Get all trip expenses for this driver in the selected month
        trip_expenses = TripExpense.objects.filter(
            bus_assignment__driver=driver,
            bus_assignment__reservation_request__org=self.request.user.profile.org,
            recorded_at__year=year,
            recorded_at__month=month
        ).select_related(
            'bus_assignment__bus',
            'bus_assignment__reservation_request__institution'
        ).order_by('-recorded_at')
        
        context['trip_expenses'] = trip_expenses
        context['month_year'] = f"{datetime(year, month, 1).strftime('%B %Y')}"
        
        return context


class StopTransferManagementView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, RegistrationClosedOnlyAccessMixin, TemplateView):
    """
    View to display the drag-and-drop interface for transferring stops between routes.
    This view provides a visual interface where stops can be dragged from one route to another.
    
    Attributes:
        template_name (str): The template for the stop transfer management page.
    
    Methods:
        get_context_data: Provides registration and all its routes with their stops to the template.
    """
    template_name = 'central_admin/stop_transfer_management.html'
    
    def get_context_data(self, **kwargs):
        """
        Add registration and all routes with their stops to the context.
        
        Returns:
            dict: Context data with registration and routes.
        """
        context = super().get_context_data(**kwargs)
        registration_slug = self.kwargs['registration_slug']
        registration = get_object_or_404(
            Registration, 
            slug=registration_slug, 
            org=self.request.user.profile.org
        )
        
        # Get all routes for this registration with their stops
        routes = Route.objects.filter(
            registration=registration,
            org=self.request.user.profile.org
        ).prefetch_related('stops', 'schedules')
        
        # Natural sorting - convert to list and sort with natural key
        routes_list = list(routes)
        routes_list.sort(key=lambda x: self._natural_sort_key(x.name))
        
        # Get all schedules for this registration
        all_schedules = Schedule.objects.filter(
            registration=registration,
            org=self.request.user.profile.org
        )
        
        context['registration'] = registration
        context['routes'] = routes_list
        context['all_schedules'] = all_schedules
        
        return context
    
    def _natural_sort_key(self, text):
        """
        Generate a key for natural sorting that handles numbers correctly.
        Converts 'Route 10' to come after 'Route 9' instead of after 'Route 1'.
        """
        import re
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


class TransferStopAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to handle stop transfer between routes.
    This view processes POST requests to move a stop from one route to another,
    updates all related tickets, and recalculates trip booking counts.
    
    Methods:
        post: Handles the stop transfer operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to transfer a stop from source route to target route.
        
        Request JSON format:
        {
            "stop_slug": "stop-slug",
            "target_route_slug": "target-route-slug"
        }
        
        Returns:
            JsonResponse: Success or error message with updated data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            stop_slug = data.get('stop_slug')
            target_route_slug = data.get('target_route_slug')
            registration_slug = self.kwargs['registration_slug']
            
            if not stop_slug or not target_route_slug:
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required parameters: stop_slug and target_route_slug'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Get the stop
            stop = get_object_or_404(
                Stop,
                slug=stop_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Get the target route
            target_route = get_object_or_404(
                Route,
                slug=target_route_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Check if stop is already in target route
            if stop.route.id == target_route.id:
                return JsonResponse({
                    'success': False,
                    'message': f"Stop '{stop.name}' is already in route '{target_route.name}'"
                }, status=400)
            
            # Store source route name for logging
            source_route_name = stop.route.name
            
            # Perform the transfer using the existing utility function
            move_stop_and_update_tickets(stop, target_route)
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Transferred stop via drag-and-drop",
                description=f"Moved stop '{stop.name}' from route '{source_route_name}' to route '{target_route.name}' in registration '{registration.name}'"
            )
            
            # Get updated stop count for both routes
            source_route = Route.objects.get(name=source_route_name, registration=registration)
            source_stop_count = source_route.stops.count()
            target_stop_count = target_route.stops.count()
            
            return JsonResponse({
                'success': True,
                'message': f"Stop '{stop.name}' successfully transferred from '{source_route_name}' to '{target_route.name}'. All tickets and trip counts have been updated.",
                'stop': {
                    'slug': stop.slug,
                    'name': stop.name,
                    'new_route_slug': target_route.slug,
                    'new_route_name': target_route.name
                },
                'source_route': {
                    'slug': source_route.slug,
                    'stop_count': source_stop_count
                },
                'target_route': {
                    'slug': target_route.slug,
                    'stop_count': target_stop_count
                }
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': f"Transfer failed: {str(e)}"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An unexpected error occurred: {str(e)}"
            }, status=500)


class UpdateStopNameAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to update a stop's name in real-time.
    This view processes POST requests to rename a stop and returns the updated name.
    
    Methods:
        post: Handles the stop name update operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to update a stop's name.
        
        Request JSON format:
        {
            "stop_slug": "stop-slug",
            "new_name": "New Stop Name"
        }
        
        Returns:
            JsonResponse: Success or error message with updated stop data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            stop_slug = data.get('stop_slug')
            new_name = data.get('new_name', '').strip()
            registration_slug = self.kwargs['registration_slug']
            
            if not stop_slug or not new_name:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop slug and new name are required'
                }, status=400)
            
            # Validate name length
            if len(new_name) > 200:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop name cannot exceed 200 characters'
                }, status=400)
            
            if len(new_name) < 2:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop name must be at least 2 characters'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Get the stop
            stop = get_object_or_404(
                Stop,
                slug=stop_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Store old name for logging
            old_name = stop.name
            
            # Check if name is actually different
            if old_name == new_name:
                return JsonResponse({
                    'success': False,
                    'message': 'New name is the same as the current name'
                }, status=400)
            
            # Update the stop name
            stop.name = new_name
            stop.save()
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Updated stop name",
                description=f"Renamed stop from '{old_name}' to '{new_name}' in route '{stop.route.name}' (Registration: '{registration.name}')"
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Stop renamed from '{old_name}' to '{new_name}' successfully",
                'stop': {
                    'slug': stop.slug,
                    'name': stop.name,
                    'old_name': old_name,
                    'route_slug': stop.route.slug,
                    'route_name': stop.route.name
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)


class AddStopAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to add a new stop to a route.
    This view processes POST requests to create a new stop in a specified route.
    
    Methods:
        post: Handles the stop creation operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to add a new stop to a route.
        
        Request JSON format:
        {
            "route_slug": "route-slug",
            "stop_name": "New Stop Name"
        }
        
        Returns:
            JsonResponse: Success or error message with new stop data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            stop_name = data.get('stop_name', '').strip()
            registration_slug = self.kwargs['registration_slug']
            
            if not route_slug or not stop_name:
                return JsonResponse({
                    'success': False,
                    'message': 'Route slug and stop name are required'
                }, status=400)
            
            # Validate name length
            if len(stop_name) > 200:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop name cannot exceed 200 characters'
                }, status=400)
            
            if len(stop_name) < 2:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop name must be at least 2 characters'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Get the route
            route = get_object_or_404(
                Route,
                slug=route_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Check if stop with same name already exists in this route
            if Stop.objects.filter(
                route=route,
                name__iexact=stop_name,
                org=request.user.profile.org
            ).exists():
                return JsonResponse({
                    'success': False,
                    'message': f"A stop with the name '{stop_name}' already exists in this route"
                }, status=400)
            
            # Create the new stop
            new_stop = Stop.objects.create(
                name=stop_name,
                route=route,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Created new stop",
                description=f"Added stop '{stop_name}' to route '{route.name}' (Registration: '{registration.name}')"
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Stop '{stop_name}' added successfully to route '{route.name}'",
                'stop': {
                    'slug': new_stop.slug,
                    'name': new_stop.name,
                    'route_slug': route.slug,
                    'route_name': route.name,
                    'pickup_count': 0,
                    'drop_count': 0
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)


class DeleteStopAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to delete a stop from a route.
    This view processes POST requests to delete a stop that has no associated tickets.
    
    Methods:
        post: Handles the stop deletion operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a stop.
        
        Request JSON format:
        {
            "stop_slug": "stop-slug"
        }
        
        Returns:
            JsonResponse: Success or error message with deleted stop data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            stop_slug = data.get('stop_slug')
            registration_slug = self.kwargs['registration_slug']
            
            if not stop_slug:
                return JsonResponse({
                    'success': False,
                    'message': 'Stop slug is required'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Get the stop
            stop = get_object_or_404(
                Stop,
                slug=stop_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Check if stop has any associated tickets (pickup or drop)
            pickup_count = stop.ticket_pickups.count()
            drop_count = stop.ticket_drops.count()
            
            if pickup_count > 0 or drop_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f"Cannot delete stop '{stop.name}' because it has {pickup_count} pickup(s) and {drop_count} drop(s) associated with it. Please reassign or delete the tickets first."
                }, status=400)
            
            # Store stop info for response
            stop_name = stop.name
            route_slug = stop.route.slug
            route_name = stop.route.name
            
            # Delete the stop
            stop.delete()
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Deleted stop",
                description=f"Deleted stop '{stop_name}' from route '{route_name}' (Registration: '{registration.name}')"
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Stop '{stop_name}' deleted successfully from route '{route_name}'",
                'stop': {
                    'slug': stop_slug,
                    'name': stop_name,
                    'route_slug': route_slug,
                    'route_name': route_name
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)


class CreateRouteAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to create a new route in a registration.
    This view processes POST requests to create a route with a given name.
    
    Methods:
        post: Handles the route creation operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new route.
        
        Request JSON format:
        {
            "route_name": "Route Name"
        }
        
        Returns:
            JsonResponse: Success or error message with created route data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            route_name = data.get('route_name', '').strip()
            registration_slug = self.kwargs['registration_slug']
            
            if not route_name:
                return JsonResponse({
                    'success': False,
                    'message': 'Route name is required'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Check if route with same name already exists in this registration
            if Route.objects.filter(
                name__iexact=route_name,
                registration=registration,
                org=request.user.profile.org
            ).exists():
                return JsonResponse({
                    'success': False,
                    'message': f"A route with name '{route_name}' already exists in this registration"
                }, status=400)
            
            # Create the route
            route = Route.objects.create(
                name=route_name,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Created route",
                description=f"Created route '{route.name}' in registration '{registration.name}'"
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Route '{route.name}' created successfully",
                'route': {
                    'slug': route.slug,
                    'name': route.name,
                    'stop_count': 0
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)


class DeleteRouteAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    AJAX API endpoint to delete a route from a registration.
    This view processes POST requests to delete a route that has no associated stops.
    
    Methods:
        post: Handles the route deletion operation and returns JSON response.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a route.
        
        Request JSON format:
        {
            "route_slug": "route-slug"
        }
        
        Returns:
            JsonResponse: Success or error message with deleted route data.
        """
        import json
        
        try:
            # Parse JSON body
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            registration_slug = self.kwargs['registration_slug']
            
            if not route_slug:
                return JsonResponse({
                    'success': False,
                    'message': 'Route slug is required'
                }, status=400)
            
            # Get the registration
            registration = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=request.user.profile.org
            )
            
            # Get the route
            route = get_object_or_404(
                Route,
                slug=route_slug,
                registration=registration,
                org=request.user.profile.org
            )
            
            # Check if route has any stops
            stop_count = route.stops.count()
            
            if stop_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f"Cannot delete route '{route.name}' because it has {stop_count} stop(s) associated with it. Please delete or transfer the stops first."
                }, status=400)
            
            # Check if route has any trips (bus assignments)
            trip_count = route.trips.count()
            
            if trip_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f"Cannot delete route '{route.name}' because it has {trip_count} trip(s) assigned to it. Please remove bus assignments first."
                }, status=400)
            
            # Store route info for response
            route_name = route.name
            route_slug_value = route.slug
            
            # Delete the route
            route.delete()
            
            # Log the activity
            log_user_activity(
                user=request.user,
                action=f"Deleted route",
                description=f"Deleted route '{route_name}' from registration '{registration.name}'"
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Route '{route_name}' deleted successfully",
                'route': {
                    'slug': route_slug_value,
                    'name': route_name
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            }, status=500)





class ManageRouteSchedulesAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            registration_slug = self.kwargs['registration_slug']
            route_slug = request.GET.get('route_slug')
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            all_schedules = Schedule.objects.filter(registration=registration, org=request.user.profile.org).values('slug', 'name', 'start_time', 'end_time')
            route_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'route': {'slug': route.slug, 'name': route.name}, 'route_schedules': list(route_schedules), 'all_schedules': list(all_schedules)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            schedule_slugs = data.get('schedule_slugs', [])
            registration_slug = self.kwargs['registration_slug']
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            if not schedule_slugs or not isinstance(schedule_slugs, list):
                return JsonResponse({'success': False, 'message': 'Schedule slugs must be provided as a list'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            schedules = Schedule.objects.filter(slug__in=schedule_slugs, registration=registration, org=request.user.profile.org)
            if schedules.count() != len(schedule_slugs):
                return JsonResponse({'success': False, 'message': 'One or more schedule slugs are invalid'}, status=400)
            route.schedules.add(*schedules)
            schedule_names = ', '.join([s.name for s in schedules])
            log_user_activity(user=request.user, action=f'Added schedules to route', description=f"Added schedules ({schedule_names}) to route '{route.name}' in registration '{registration.name}'")
            updated_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'message': f"Schedules added to route '{route.name}' successfully", 'route': {'slug': route.slug, 'name': route.name}, 'schedules': list(updated_schedules)})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
    def delete(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            schedule_slugs = data.get('schedule_slugs', [])
            registration_slug = self.kwargs['registration_slug']
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            if not schedule_slugs or not isinstance(schedule_slugs, list):
                return JsonResponse({'success': False, 'message': 'Schedule slugs must be provided as a list'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            schedules = Schedule.objects.filter(slug__in=schedule_slugs, registration=registration, org=request.user.profile.org)
            route.schedules.remove(*schedules)
            schedule_names = ', '.join([s.name for s in schedules])
            log_user_activity(user=request.user, action=f'Removed schedules from route', description=f"Removed schedules ({schedule_names}) from route '{route.name}' in registration '{registration.name}'")
            updated_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'message': f"Schedules removed from route '{route.name}' successfully", 'route': {'slug': route.slug, 'name': route.name}, 'schedules': list(updated_schedules)})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


class ManageRouteSchedulesAPIView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            registration_slug = self.kwargs['registration_slug']
            route_slug = request.GET.get('route_slug')
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            all_schedules = Schedule.objects.filter(registration=registration, org=request.user.profile.org).values('slug', 'name', 'start_time', 'end_time')
            route_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'route': {'slug': route.slug, 'name': route.name}, 'route_schedules': list(route_schedules), 'all_schedules': list(all_schedules)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            schedule_slugs = data.get('schedule_slugs', [])
            registration_slug = self.kwargs['registration_slug']
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            if not schedule_slugs or not isinstance(schedule_slugs, list):
                return JsonResponse({'success': False, 'message': 'Schedule slugs must be provided as a list'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            schedules = Schedule.objects.filter(slug__in=schedule_slugs, registration=registration, org=request.user.profile.org)
            if schedules.count() != len(schedule_slugs):
                return JsonResponse({'success': False, 'message': 'One or more schedule slugs are invalid'}, status=400)
            route.schedules.add(*schedules)
            schedule_names = ', '.join([s.name for s in schedules])
            log_user_activity(user=request.user, action=f'Added schedules to route', description=f"Added schedules ({schedule_names}) to route '{route.name}' in registration '{registration.name}'")
            updated_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'message': f"Schedules added to route '{route.name}' successfully", 'route': {'slug': route.slug, 'name': route.name}, 'schedules': list(updated_schedules)})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
    def delete(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            route_slug = data.get('route_slug')
            schedule_slugs = data.get('schedule_slugs', [])
            registration_slug = self.kwargs['registration_slug']
            if not route_slug:
                return JsonResponse({'success': False, 'message': 'Route slug is required'}, status=400)
            if not schedule_slugs or not isinstance(schedule_slugs, list):
                return JsonResponse({'success': False, 'message': 'Schedule slugs must be provided as a list'}, status=400)
            registration = get_object_or_404(Registration, slug=registration_slug, org=request.user.profile.org)
            route = get_object_or_404(Route, slug=route_slug, registration=registration, org=request.user.profile.org)
            schedules = Schedule.objects.filter(slug__in=schedule_slugs, registration=registration, org=request.user.profile.org)
            route.schedules.remove(*schedules)
            schedule_names = ', '.join([s.name for s in schedules])
            log_user_activity(user=request.user, action=f'Removed schedules from route', description=f"Removed schedules ({schedule_names}) from route '{route.name}' in registration '{registration.name}'")
            updated_schedules = route.schedules.all().values('slug', 'name', 'start_time', 'end_time')
            return JsonResponse({'success': True, 'message': f"Schedules removed from route '{route.name}' successfully", 'route': {'slug': route.slug, 'name': route.name}, 'schedules': list(updated_schedules)})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


class InstallmentDateListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = None
    template_name = 'central_admin/installment_date_list.html'
    context_object_name = 'installment_dates'
    paginate_by = 50
    
    def dispatch(self, request, *args, **kwargs):
        from services.models import InstallmentDate
        self.model = InstallmentDate
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        registration = get_object_or_404(Registration, slug=registration_slug, org=self.request.user.profile.org)
        return self.model.objects.filter(registration=registration, org=self.request.user.profile.org).order_by('due_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration_slug = self.kwargs.get('registration_slug')
        context['registration'] = get_object_or_404(Registration, slug=registration_slug, org=self.request.user.profile.org)
        return context


class InstallmentDateCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
    model = None
    template_name = 'central_admin/installment_date_form.html'
    form_class = None
    
    def dispatch(self, request, *args, **kwargs):
        from services.models import InstallmentDate
        from services.forms.central_admin import InstallmentDateForm
        self.model = InstallmentDate
        self.form_class = InstallmentDateForm
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        installment = form.save(commit=False)
        installment.org = self.request.user.profile.org
        
        # Auto-assign registration from URL
        registration_slug = self.kwargs.get('registration_slug')
        registration = get_object_or_404(Registration, slug=registration_slug, org=self.request.user.profile.org)
        installment.registration = registration
        
        installment.save()
        log_user_activity(user=self.request.user, action='Created installment date', description=f"Created installment for {installment.registration.name} due on {installment.due_date}")
        messages.success(self.request, f"Installment date created successfully!")
        return redirect('central_admin:installment_date_list', registration_slug=installment.registration.slug)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registration_slug = self.kwargs.get('registration_slug')
        if registration_slug:
            context['registration'] = get_object_or_404(Registration, slug=registration_slug, org=self.request.user.profile.org)
        return context


class InstallmentDateUpdateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, UpdateView):
    model = None
    template_name = 'central_admin/installment_date_form.html'
    form_class = None
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def dispatch(self, request, *args, **kwargs):
        from services.models import InstallmentDate
        from services.forms.central_admin import InstallmentDateForm
        self.model = InstallmentDate
        self.form_class = InstallmentDateForm
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return self.model.objects.filter(org=self.request.user.profile.org)
    
    def form_valid(self, form):
        installment = form.save()
        log_user_activity(user=self.request.user, action='Updated installment date', description=f"Updated installment for {installment.registration.name} due on {installment.due_date}")
        messages.success(self.request, f"Installment date updated successfully!")
        return redirect('central_admin:installment_date_list', registration_slug=installment.registration.slug)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.object.registration
        return context


class InstallmentDateDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = None
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def dispatch(self, request, *args, **kwargs):
        from services.models import InstallmentDate
        self.model = InstallmentDate
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return self.model.objects.filter(org=self.request.user.profile.org)
    
    def get_success_url(self):
        registration_slug = self.object.registration.slug
        log_user_activity(user=self.request.user, action='Deleted installment date', description=f"Deleted installment for {self.object.registration.name} due on {self.object.due_date}")
        messages.success(self.request, f"Installment date deleted successfully!")
        return reverse('central_admin:installment_date_list', kwargs={'registration_slug': registration_slug})


class PaymentListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View to list all payments across all institutions for central admin.
    
    Attributes:
        model (Payment): The Payment model to query.
        template_name (str): Template for displaying payments list.
        context_object_name (str): Context variable name for payments.
        paginate_by (int): Number of payments per page.
    """
    model = None  # Will be imported dynamically
    template_name = 'central_admin/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 50
    
    def dispatch(self, request, *args, **kwargs):
        # Import Payment model here to avoid circular import
        from services.models import Payment
        self.model = Payment
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Returns payments filtered by organization and registration.
        """
        queryset = self.model.objects.filter(
            org=self.request.user.profile.org
        ).select_related('ticket', 'registration', 'institution', 'installment_date', 'recorded_by')
        
        # Filter by registration
        registration_slug = self.kwargs.get('registration_slug')
        if registration_slug:
            queryset = queryset.filter(registration__slug=registration_slug)
        
        # Filter by ticket if provided in query params
        ticket_slug = self.request.GET.get('ticket')
        if ticket_slug:
            queryset = queryset.filter(ticket__slug=ticket_slug)
        
        return queryset.order_by('-payment_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        """
        Adds registration info to context.
        """
        context = super().get_context_data(**kwargs)
        registration_slug = self.kwargs.get('registration_slug')
        if registration_slug:
            context['registration'] = get_object_or_404(
                Registration,
                slug=registration_slug,
                org=self.request.user.profile.org
            )
        return context
