import threading
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from core.models import UserProfile
from django.db import transaction, IntegrityError
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Q, Count, F
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib import messages
from urllib.parse import urlencode
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
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
    BusRequestCommentForm
)

from services.tasks import process_uploaded_route_excel, send_email_task, export_tickets_to_excel, process_uploaded_bus_excel


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
        context['org'] = self.request.user.profile.org
        context['active_registrations'] = Registration.objects.filter(org=self.request.user.profile.org).count()
        context['buses_available'] = Bus.objects.filter(org=self.request.user.profile.org).count()
        context['institution_count'] = Institution.objects.filter(org=self.request.user.profile.org).count()
        context['recent_activities'] = UserActivity.objects.filter(org=self.request.user.profile.org).order_by('-timestamp')[:10]
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
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, is_institution_admin=True)
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
        form.fields['incharge'].queryset = UserProfile.objects.filter(org=self.request.user.profile.org, is_institution_admin=True)
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
            queryset = BusRecord.objects.filter(org=self.request.user.profile.org, bus=None, registration__slug=self.kwargs["registration_slug"]).order_by('label')
        else:
            queryset = BusRecord.objects.filter(org=self.request.user.profile.org, registration__slug=self.kwargs["registration_slug"]).order_by('label')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
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
    model = BusRecord
    template_name = 'central_admin/bus_record_update.html'
    form_class = BusRecordUpdateForm
    slug_field = 'slug'
    slug_url_kwarg = 'bus_record_slug'

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
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        return context

    def get_success_url(self):
        return reverse('central_admin:bus_record_list', kwargs={'registration_slug': self.kwargs['registration_slug']})
    

class TripListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Trip
    template_name = 'central_admin/trip_list.html'
    context_object_name = 'trips'
    
    def get_queryset(self):
        bus_record = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        queryset = Trip.objects.filter(record=bus_record)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context["bus_record"] = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        return context
    

class TripCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = Trip
    template_name = 'central_admin/trip_confirm_delete.html'
    slug_field = 'id'
    slug_url_kwarg = 'trip_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = Registration.objects.get(slug=self.kwargs["registration_slug"])
        context['bus_record'] = BusRecord.objects.get(slug=self.kwargs["bus_record_slug"])
        return context
    
    def get_success_url(self):
        return reverse('central_admin:trip_list', kwargs={'registration_slug': self.kwargs['registration_slug'], 'bus_record_slug': self.kwargs['bus_record_slug']})

    
class PeopleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = UserProfile
    template_name = 'central_admin/people_list.html'
    context_object_name = 'people'
    
    def get_queryset(self):
        queryset = UserProfile.objects.filter(org=self.request.user.profile.org)
        return queryset
    

class PeopleCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = UserProfile
    form_class = PeopleUpdateForm
    template_name = 'central_admin/people_update.html'
    success_url = reverse_lazy('central_admin:people_list')

    def form_valid(self, form):
        return super().form_valid(form)
    

class PeopleDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
    model = UserProfile
    template_name = 'central_admin/people_confirm_delete.html'
    success_url = reverse_lazy('central_admin:people_list')


class RouteListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Route
    template_name = 'central_admin/route_list.html'
    context_object_name = 'routes'
    paginate_by = 10  # Add pagination with 10 items per page

    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        self.search_term = self.request.GET.get('search', '')
        queryset = Route.objects.filter(org=self.request.user.profile.org, registration=registration)
        if self.search_term:
            queryset = queryset.filter(name__icontains=self.search_term)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = Registration.objects.get(slug=self.kwargs['registration_slug'])
        context["search_term"] = self.search_term
        return context
    

class RouteFileUploadView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = Stop
    template_name = 'central_admin/stop_list.html'
    context_object_name = 'stops'
    
    def get_queryset(self):
        route = Route.objects.get(slug=self.kwargs['route_slug'])
        registration = Registration.objects.get(slug=self.kwargs['registration_slug'])
        queryset = Stop.objects.filter(registration=registration, route=route)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = Route.objects.get(slug=self.kwargs['route_slug'])
        context["registration"] = Registration.objects.get(slug=self.kwargs['registration_slug'])
        return context
    

class StopCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = Registration
    template_name = 'central_admin/registration_list.html'
    context_object_name = 'registrations'
    
    def get_queryset(self):
        queryset = Registration.objects.filter(org=self.request.user.profile.org)
        return queryset
    
    
class RegistrationCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = Registration
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'registration_slug'
    success_url = reverse_lazy('central_admin:registration_list')
    
    
class TicketListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    model = Ticket
    template_name = 'central_admin/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 15
    
    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)
        
        # Base queryset filtered by registration and institution
        queryset = Ticket.objects.filter(org=self.request.user.profile.org, registration=self.registration).order_by('-created_at')
        
        # Apply filters based on GET parameters
        institution = self.request.GET.get('institution')
        pickup_points = self.request.GET.getlist('pickup_point')
        drop_points = self.request.GET.getlist('drop_point')
        schedule = self.request.GET.get('schedule')
        pickup_buses = self.request.GET.getlist('pickup_bus')
        drop_buses = self.request.GET.getlist('drop_bus')
        student_group = self.request.GET.get('student_group')
        filters = False  # Default no filters applied
        
        self.search_term = self.request.GET.get('search', '')
        
        if self.search_term:
            queryset = Ticket.objects.filter(
                Q(student_name__icontains=self.search_term) |
                Q(student_email__icontains=self.search_term) |
                Q(student_id__icontains=self.search_term) |
                Q(contact_no__icontains=self.search_term) |
                Q(alternative_contact_no__icontains=self.search_term)
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
        
        # Pass the filters flag to context (done in get_context_data)
        self.filters = filters  # Store in the instance for later access

        return queryset
    
    def get_context_data(self, **kwargs):
        # Get default context from parent
        context = super().get_context_data(**kwargs)
        
        # Add the filter status to the context
        context['filters'] = self.filters  # Pass the filters flag to the template
        
        # Add the filter options to the context
        context['registration'] = self.registration
        context['pickup_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration).order_by('name')
        context['drop_points'] = Stop.objects.filter(org=self.registration.org, registration=self.registration).order_by('name')
        context['schedules'] = Schedule.objects.filter(org=self.registration.org, registration=self.registration)
        context['institutions'] = Institution.objects.filter(org=self.registration.org)
        context['bus_records'] = BusRecord.objects.filter(org=self.registration.org, registration=self.registration).order_by("label")
        context['student_groups'] = StudentGroup.objects.filter(org = self.request.user.profile.org).order_by('name')
        context['search_term'] = self.search_term

        return context
    

class TicketFilterView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
    """
    View to filter tickets by a date range, institution, and ticket type.
    """
    model = Ticket
    template_name = 'central_admin/ticket_filter.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        registration_slug = self.kwargs.get('registration_slug')
        self.registration = get_object_or_404(Registration, slug=registration_slug)

        queryset = Ticket.objects.filter(org=self.request.user.profile.org, registration=self.registration)

        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        institution_slug = self.request.GET.get('institution')  # Changed to slug
        ticket_type = self.request.GET.get('ticket_type')
        student_group_id = self.request.GET.get('student_group')

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
        return context


class FAQCreateView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, CreateView):
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
    model = FAQ
    template_name = 'central_admin/registration_confirm_delete.html'
    slug_url_kwarg = 'faq_slug'
    
    def get_success_url(self):
        return reverse('central_admin:registration_update', kwargs={'slug': self.kwargs['registration_slug']})
    

class ScheduleListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
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
    model = BusRequest
    template_name = 'central_admin/bus_request_list.html'
    context_object_name = 'bus_requests'
    paginate_by = 20
    
    def get_queryset(self):
        registration = Registration.objects.get(slug=self.kwargs["registration_slug"])
        queryset = BusRequest.objects.filter(org=self.request.user.profile.org, registration=registration).order_by('-created_at')
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
        return context

class BusRequestOpenListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
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
        return context

class BusRequestClosedListView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, ListView):
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
        return context

class BusRequestDeleteView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, DeleteView):
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
        }

        # Trigger the Celery task
        export_tickets_to_excel.apply_async(
            args=[request.user.id, registration_slug, search_term, filters]
        )

        return JsonResponse({"message": "Export request received. You will be notified once the export is ready."})


class StudentGroupFilterView(LoginRequiredMixin, CentralAdminOnlyAccessMixin, View):
    """
    View to filter student groups based on the selected institution.
    """
    def get(self, request, *args, **kwargs):
        institution_slug = request.GET.get('institution')
        student_groups = StudentGroup.objects.filter(institution__slug=institution_slug).order_by('name') if institution_slug else []
        return render(request, 'central_admin/partials/student_group_options.html', {'student_groups': student_groups})

